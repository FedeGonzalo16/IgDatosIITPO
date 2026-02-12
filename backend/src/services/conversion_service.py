from src.config.database import get_mongo, get_redis
from bson import ObjectId
import json
from datetime import datetime

class ConversionService:
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
            if not rule: raise Exception("Regla no encontrada")
        
        # 2. Obtener Calificación
        calif = db.calificaciones.find_one({"_id": ObjectId(data['calificacion_id'])})
        nota_orig = str(calif['valor_original']['nota'])
        
        # 3. Calcular (Lógica simple de mapeo)
        valor_conv = None
        for m in rule.get('mapeo', []):
            if str(m['nota_origen']) == nota_orig:
                valor_conv = m['nota_destino']
                break
        
        if not valor_conv: raise Exception("No hay equivalencia en la regla")
        
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