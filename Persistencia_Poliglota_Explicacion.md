# Persistencia Políglota — Cómo se arma y por qué

---

## ¿Qué es la Persistencia Políglota?

Es la decisión arquitectónica de **no usar una sola base de datos para todo**, sino elegir el motor más adecuado para cada tipo de problema dentro del mismo sistema. El término lo popularizó Martin Fowler: cada base de datos "habla su propio idioma" y cada una resuelve algo que las otras no hacen bien.

---

## Los pasos para armarlo

### 1. Analizar el dominio y separar los problemas

El primer paso es no pensar en bases de datos, sino en **qué tipos de preguntas le vas a hacer al sistema**. Cada tipo de pregunta tiene una estructura de datos óptima:

| Tipo de pregunta | Estructura óptima |
|---|---|
| "Guardame este documento con estructura variable" | Documental (MongoDB) |
| "¿Cuántos saltos hay entre A y B?" | Grafos (Neo4j) |
| "Dime este valor YA, es consultado miles de veces por segundo" | Clave-Valor (Redis) |
| "Guardá todo, nunca borres nada, escribí millones de filas" | Columnar (Cassandra) |

**En EduGrade** este análisis dio:
- Las calificaciones tienen estructura variable según el país → **MongoDB**
- Las trayectorias académicas son un grafo de relaciones → **Neo4j**
- Las reglas de conversión se consultan constantemente → **Redis**
- Los logs de auditoría son inmutables y masivos → **Cassandra**

---

### 2. Definir qué es la "Fuente de Verdad" de cada dato

En persistencia políglota el dato puede vivir en más de un motor a la vez. Hay que decidir claramente **cuál es el dueño de cada dato**:

- La fuente de verdad para los **datos** (nombre, legajo, nota guardada) es **MongoDB**.
- La fuente de verdad para las **relaciones** (quién cursó qué, qué materia equivale a cuál) es **Neo4j**.
- **Redis** no es fuente de verdad de nada: es un espejo de velocidad.
- **Cassandra** no se modifica: solo acumula.

Esto es fundamental porque cuando hay conflicto, sabés a quién creerle.

---

### 3. Sincronización a nivel de aplicación (no a nivel de base de datos)

Este es el punto más importante conceptualmente: **las bases de datos no se hablan entre sí**. No hay triggers cruzados, no hay foreign keys entre MongoDB y Neo4j. La consistencia entre motores la garantiza el código de la capa de servicio.

En EduGrade se implementó lo que se llama **dual-write**: cada vez que se crea un estudiante, el servicio hace dos escrituras en la misma función:

```python
# StudentService.create()
db.estudiantes.insert_one(doc)          # 1. Escribe en MongoDB
session.run("MERGE (e:Estudiante...)")  # 2. Escribe en Neo4j
MetadataService.save_metadata(...)      # 3. Escribe en Cassandra
```

Si una de esas escrituras falla, el sistema lo maneja (en este caso loggea el error). En sistemas de producción más críticos se usaría un patrón **Saga** o **Outbox** para garantizar que las tres escrituras terminen eventualmente.

---

### 4. Aplicar el teorema CAP a cada motor de forma consciente

Al tener múltiples bases, podés elegir el trade-off CAP **por componente** en lugar de para todo el sistema. Esa es una ventaja enorme de la persistencia políglota.

| Motor | Clasificación | Configuración | Razonamiento |
|---|---|---|---|
| MongoDB | **CP** | N=3, R=2, W=2 | Prefiere rechazar una escritura antes que guardar una nota inconsistente |
| Neo4j | **CP** | N=3, R=2, W=2 | Una relación de equivalencia faltante puede invalidar una titulación |
| Redis | **CP** | N=3, R=2, W=2 | Servir una regla de conversión desactualizada genera errores en masa |
| Cassandra | **AP** | N=3, R=1, W=1 | El sistema de auditoría nunca debe dejar de registrar eventos |

La pregunta que hay que poder responder por cada componente es:
> *"¿Qué es peor: que falle la escritura, o que guarde algo inconsistente?"*

Para la auditoría es peor no guardar nada. Para una nota de examen es peor guardar un dato viejo.

---

### 5. Patrón de caché: Cache-Aside

Cuando un dato vive en dos lugares (base principal + caché), el patrón estándar es **Cache-Aside**:

```
1. Buscar en Redis
2. Si está  →  devolverlo  (cache hit, sub-milisegundo)
3. Si no está  →  buscar en MongoDB, guardar en Redis, devolver
```

El código siempre mantiene Redis actualizado: al crear o modificar una regla de conversión, la función actualiza MongoDB **y** refresca la clave en Redis en la misma operación. Así nunca se sirven datos desactualizados.

```python
# ConversionService.aplicar_conversion()
rule_json = redis.get(f"regla:{codigo_regla}")
if rule_json:
    rule = json.loads(rule_json)                   # Cache hit
else:
    rule = db.reglas_conversion.find_one(...)      # Fallback a MongoDB
    redis.setex(f"regla:{codigo}", 604800, ...)    # Poblar caché (TTL 7 días)
```

---

### 6. Definir la estrategia de borrado

En sistemas políglotas esto se complica porque el dato puede vivir en varios lugares. La decisión en EduGrade fue:

| Motor | Estrategia | Motivo |
|---|---|---|
| **MongoDB** | Soft delete (`estado: "INACTIVO"`) | El documento queda; se filtra en consultas. Preserva historial documental. |
| **Neo4j** | Hard delete (`DETACH DELETE`) | Relaciones "fantasma" hacia nodos eliminados romperían las trayectorias académicas. |
| **Cassandra** | Nada se borra nunca | Solo se agrega un nuevo registro de estado. Append-only por diseño. |

La regla general es: **el motor que es fuente de verdad del dato decide si se borra o no**.

---

## Resumen conceptual en una frase

> En persistencia políglota, la consistencia no la garantiza ninguna base de datos sola: la garantiza la **capa de servicio de la aplicación**, que sabe qué escribir, en qué orden, en qué motor, y a quién creerle cuando hay conflicto.

Las bases de datos son herramientas especializadas. El código que las orquesta es quien define el contrato de consistencia del sistema.

---

## Diagrama mental

```
                  ┌─────────────────────┐
                  │   Capa de Servicio  │  ← Aquí vive la consistencia
                  │   (Python / Flask)  │
                  └──────┬──────────────┘
                         │
          ┌──────────────┼──────────────┬──────────────┐
          ▼              ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ MongoDB  │   │  Neo4j   │   │  Redis   │   │Cassandra │
    │          │◄─►│          │   │          │   │          │
    │ Fuente   │   │ Fuente   │   │  Espejo  │   │ Log      │
    │ de verdad│   │ de verdad│   │ de vel.  │   │ inmutable│
    │ (datos)  │   │ (relac.) │   │          │   │          │
    │   CP     │   │   CP     │   │   CP     │   │   AP     │
    └──────────┘   └──────────┘   └──────────┘   └──────────┘
         ▲               ▲
         └── Dual-write ─┘
```
