from src.config.database import get_mongo, get_redis, get_cassandra
from bson import ObjectId
import json
from datetime import datetime

class ConversionService:
    @staticmethod
    def _buscar_equivalencia(mapeo, nota_orig, nota_orig_str):
        """Busca equivalencia en mapeo"""
        for m in mapeo:
            orig = m.get('nota_origen')
            orig_str = str(orig)
            if orig_str == nota_orig_str:
                return m['nota_destino']
            if isinstance(orig, (int, float)) and isinstance(nota_orig, (int, float)):
                if abs(float(orig) - float(nota_orig)) < 0.01:
                    return m['nota_destino']
            if isinstance(orig, str) and isinstance(nota_orig, str) and orig.upper() == nota_orig.upper():
                return m['nota_destino']
        return None

    @staticmethod
    def create_rule(data):
        db = get_mongo()
        redis = get_redis()
        
        # 1. Guardar en Mongo
        res = db.reglas_conversion.insert_one(data)
        
        # 2. Cachear en Redis
        key = f"regla:{data['codigo_regla']}"
        data['_id'] = str(res.inserted_id)
        redis.setex(key, 604800, json.dumps(data, default=str)) # 7 días TTL
        
        return str(res.inserted_id)

    @staticmethod
    def get_all_rules():
        """Lista todas las reglas de conversión desde Mongo."""
        db = get_mongo()
        reglas = list(db.reglas_conversion.find())
        for r in reglas:
            r["_id"] = str(r["_id"])
        return reglas

    @staticmethod
    def get_rule_by_id(regla_id):
        """Obtiene una regla por ID."""
        db = get_mongo()
        regla = db.reglas_conversion.find_one({"_id": ObjectId(regla_id)})
        if regla:
            regla["_id"] = str(regla["_id"])
        return regla

    @staticmethod
    def aplicar_conversion(data):
        # data: {calificacion_id, codigo_regla}
        db = get_mongo()
        redis = get_redis()
        
        # 1. Buscar regla en Redis (Cache-Aside)
        rule_json = redis.get(f"regla:{data['codigo_regla']}")
        if rule_json:
            rule = json.loads(rule_json)
        else:
            # Fallback a Mongo
            rule = db.reglas_conversion.find_one({"codigo_regla": data['codigo_regla']})
            if not rule:
                raise Exception("Regla no encontrada")
        
        # 2. Obtener Calificación
        calif = db.calificaciones.find_one({"_id": ObjectId(data['calificacion_id'])})
        nota_orig = calif['valor_original']['nota']
        nota_orig_str = str(nota_orig)
        
        # 3. Calcular (mapeo con soporte para letras y números)
        valor_conv = ConversionService._buscar_equivalencia(rule.get('mapeo', []), nota_orig, nota_orig_str)
        
        if valor_conv is None:
            raise Exception("No hay equivalencia en la regla")
        
        # 4. Actualizar Mongo (Append only en array)
        conversion_doc = {
            "regla": data['codigo_regla'],
            "valor_convertido": valor_conv,
            "fecha": datetime.utcnow()
        }
        db.calificaciones.update_one(
            {"_id": ObjectId(data['calificacion_id'])},
            {"$push": {"conversiones_aplicadas": conversion_doc}}
        )
        
        return valor_conv

    @staticmethod
    def update_rule(regla_id, data, modificado_por=None):
        """
        Actualiza una regla en Mongo y Redis. Antes de actualizar, guarda el estado
        anterior en Cassandra (historico_reglas) para auditoría y re-cálculo de notas antiguas.
        """
        db = get_mongo()
        redis = get_redis()

        #Obtener estado anterior
        regla_actual = db.reglas_conversion.find_one({"_id": ObjectId(regla_id)})
        if not regla_actual:
            raise ValueError("Regla no encontrada")

        #Guardar estado anterior en Cassandra para auditoría
        session_cass = get_cassandra()
        if session_cass:
            try:
                regla_anterior_json = json.dumps({
                    "codigo_regla": regla_actual.get("codigo_regla"),
                    "mapeo": regla_actual.get("mapeo", []),
                    "nombre": regla_actual.get("nombre"),
                    "updated_at": datetime.utcnow().isoformat(),
                }, default=str)
                session_cass.execute("""
                    INSERT INTO historico_reglas (id_regla, fecha_cambio, id_historico, regla_anterior, modificado_por)
                    VALUES (%s, toTimestamp(now()), uuid(), %s, %s)
                """, (regla_id, regla_anterior_json, modificado_por or ""))
            except Exception as e:
                print(f"[WARNING] No se pudo guardar historico_reglas en Cassandra: {e}")

        #Actualizar Mongo
        update_data = {}
        if "codigo_regla" in data:
            update_data["codigo_regla"] = data["codigo_regla"]
        if "mapeo" in data:
            update_data["mapeo"] = data["mapeo"]
        if "nombre" in data:
            update_data["nombre"] = data["nombre"]
        db.reglas_conversion.update_one({"_id": ObjectId(regla_id)}, {"$set": update_data})

        #Actualizar cache en Redis (invalidar o refrescar)
        codigo = data.get("codigo_regla", regla_actual.get("codigo_regla"))
        key = f"regla:{codigo}"
        regla_actualizada = db.reglas_conversion.find_one({"_id": ObjectId(regla_id)})
        regla_actualizada["_id"] = str(regla_actualizada["_id"])
        redis.setex(key, 604800, json.dumps(regla_actualizada, default=str))

        return True