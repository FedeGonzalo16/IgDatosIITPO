from neo4j import GraphDatabase

# Datos de conexión
uri = ''
usuario = ''
contrasena = ''

driver = GraphDatabase.driver(uri, auth=(usuario, contrasena))
session = driver.session()

# Nuevas entidades (personajes, lugares, películas, eventos, universos, equipos)
session.run("CREATE (:Personaje {nombre: 'Scarlet Witch', identidad: 'Wanda Maximoff'})")
session.run("CREATE (:Pelicula {titulo: 'Avengers: Infinity War', trama: 'Thanos busca las Gemas', fecha_estreno: '2018-04-27'})")

# Relaciones
session.run("""MATCH(p:Pelicula {titulo:'Avengers: Infinity War'}), c:Comic {titulo:'Infinity Gauntlet'}
              CREATE (p)-[:BASADA_EN]->(c)""")

session.run("""MATCH(p:Pelicula {titulo:'Avengers: Infinity War'}), pers:Personaje {nombre:'Scarlet Witch'}
              CREATE (p)-[:APARECE {principal: true}]->(pers)""")

session.close()
driver.close()