from src.config.database import get_mongo, get_redis, get_cassandra
from bson import ObjectId
import json
from datetime import datetime

class ConversionService:
    @staticmethod
    def _buscar_equivalencia(mapeo, nota_orig, nota_orig_str):
        """
        Soporta tres tipos de mapeo: por igualdad de string, por igualdad numérica
        (con tolerancia de punto flotante) y por igualdad de letra (case-insensitive).
        """
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
        r  = get_redis()
        
        res = db.reglas_conversion.insert_one(data)
        
        # Al crear la regla la cacheamos directamente; así el primer uso no hace hit a Mongo
        key = f"regla:{data['codigo_regla']}"
        data['_id'] = str(res.inserted_id)
        r.setex(key, 604800, json.dumps(data, default=str))  # TTL 7 días
        
        return str(res.inserted_id)

    @staticmethod
    def get_all_rules():
        db = get_mongo()
        reglas = list(db.reglas_conversion.find())
        for r in reglas:
            r["_id"] = str(r["_id"])
        return reglas

    @staticmethod
    def get_rule_by_id(regla_id):
        db = get_mongo()
        regla = db.reglas_conversion.find_one({"_id": ObjectId(regla_id)})
        if regla:
            regla["_id"] = str(regla["_id"])
        return regla

    @staticmethod
    def aplicar_conversion(data):
        """
        Patrón Cache-Aside: intenta leer la regla desde Redis antes de ir a Mongo.
        El resultado de la conversión se agrega (push) al array conversiones_aplicadas
        de la calificación, preservando el historial completo de transformaciones.
        """
        db    = get_mongo()
        redis = get_redis()
        
        # Cache-Aside: Redis primero, Mongo como fallback
        rule_json = redis.get(f"regla:{data['codigo_regla']}")
        if rule_json:
            rule = json.loads(rule_json)
        else:
            rule = db.reglas_conversion.find_one({"codigo_regla": data['codigo_regla']})
            if not rule:
                raise Exception("Regla no encontrada")
            # Cacheamos el resultado del fallback para la próxima llamada
            rule_copy = dict(rule)
            rule_copy['_id'] = str(rule_copy['_id'])
            redis.setex(f"regla:{data['codigo_regla']}", 604800, json.dumps(rule_copy, default=str))
        
        calif = db.calificaciones.find_one({"_id": ObjectId(data['calificacion_id'])})
        nota_orig     = calif['valor_original']['nota']
        nota_orig_str = str(nota_orig)
        
        valor_conv = ConversionService._buscar_equivalencia(rule.get('mapeo', []), nota_orig, nota_orig_str)
        
        if valor_conv is None:
            raise Exception("No hay equivalencia en la regla")
        
        # Usamos $push (no $set) para no perder conversiones anteriores
        conversion_doc = {
            "regla":           data['codigo_regla'],
            "valor_convertido": valor_conv,
            "fecha":           datetime.utcnow()
        }
        db.calificaciones.update_one(
            {"_id": ObjectId(data['calificacion_id'])},
            {"$push": {"conversiones_aplicadas": conversion_doc}}
        )
        
        return valor_conv

    @staticmethod
    def update_rule(regla_id, data, modificado_por=None):
        """
        Antes de modificar una regla, guarda el estado anterior en Cassandra.
        Esto permite auditar qué mapeos estaban vigentes cuando se realizó un traslado histórico.
        """
        db    = get_mongo()
        redis = get_redis()

        regla_actual = db.reglas_conversion.find_one({"_id": ObjectId(regla_id)})
        if not regla_actual:
            raise ValueError("Regla no encontrada")

        # Snapshot inmutable del estado anterior en Cassandra
        session_cass = get_cassandra()
        if session_cass:
            try:
                regla_anterior_json = json.dumps({
                    "codigo_regla": regla_actual.get("codigo_regla"),
                    "mapeo":        regla_actual.get("mapeo", []),
                    "nombre":       regla_actual.get("nombre"),
                    "updated_at":   datetime.utcnow().isoformat(),
                }, default=str)
                session_cass.execute("""
                    INSERT INTO historico_reglas (id_regla, fecha_cambio, id_historico, regla_anterior, modificado_por)
                    VALUES (%s, toTimestamp(now()), uuid(), %s, %s)
                """, (regla_id, regla_anterior_json, modificado_por or ""))
            except Exception as e:
                print(f"[WARNING] No se pudo guardar historico_reglas en Cassandra: {e}")

        update_data = {}
        if "codigo_regla" in data: update_data["codigo_regla"] = data["codigo_regla"]
        if "mapeo"        in data: update_data["mapeo"]        = data["mapeo"]
        if "nombre"       in data: update_data["nombre"]       = data["nombre"]
        db.reglas_conversion.update_one({"_id": ObjectId(regla_id)}, {"$set": update_data})

        # Refrescamos la caché con el nuevo estado para que la próxima conversión use la regla actualizada
        codigo = data.get("codigo_regla", regla_actual.get("codigo_regla"))
        regla_actualizada = db.reglas_conversion.find_one({"_id": ObjectId(regla_id)})
        regla_actualizada["_id"] = str(regla_actualizada["_id"])
        redis.setex(f"regla:{codigo}", 604800, json.dumps(regla_actualizada, default=str))

        return True
