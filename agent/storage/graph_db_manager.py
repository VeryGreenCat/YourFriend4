from utils import get_config
from neo4j import GraphDatabase

_graph_db = None
class GraphDatabase:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_User(self, user_id, user_info):
        with self.driver.session() as session:
            # Create Person node
            session.run("CREATE (p:Person {name: $name})", name=name)
            # Create Age node
            session.run("CREATE (a:Age {value: $age})", age=age)
            # Create relationship between Person and Age
            session.run("MATCH (p:Person {name: $name}), (a:Age {value: $age}) "
                        "CREATE (p)-[:HAS_AGE]->(a)", name=name, age=age)

def load():
    global _graph_db
    if _graph_db is None:
        uri = get_config('graph_db_uri')
        user = get_config('graph_db_user')
        password = get_config('graph_db_password')
        _graph_db = GraphDatabase(uri, user, password)
    return _graph_db

def close():
    global _graph_db
    if _graph_db is not None:
        _graph_db.close()
        _graph_db = None


# emotions: main->happiness, sadness, fear, disgust, anger, and surprise
# sub_emotions: 
# Admiration: Respect for someone.
# Adoration: Deep love and admiration.
# Aesthetic appreciation: Appreciation of beauty.
# Amusement: Finding something funny.
# Anger: Strong annoyance or displeasure.
# Anxiety: Worry or unease.
# Awe: Wonder or admiration.
# Awkwardness: Social discomfort.
# Boredom: Lack of interest.
# Calmness: Tranquility.
# Confusion: Lack of understanding.
# Craving: Strong desire.
# Disgust: Intense dislike.
# Empathic pain: Feeling others' suffering.
# Entrancement: Being mesmerized.
# Excitement: Great enthusiasm.
# Fear: Unpleasant emotion caused by threat.
# Horror: Intense fear or shock.
# Interest: Curiosity or concern.
# Joy: Great pleasure.
# Nostalgia: Sentimental longing.
# Relief: Alleviation of distress.
# Romance: Romantic love.
# Sadness: Unhappiness.
# Satisfaction: Fulfillment.
# Sexual desire: Physical longing.
# Surprise: Astonishment. 