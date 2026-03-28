from datetime import datetime

from agent.utils import PRIMARY_EMOTIONS, SUB_EMOTIONS, TRAIT_NODES
from agent.utils import get_config
from neo4j import GraphDatabase as _Neo4jDriver

_graph_db = None
class GraphDatabase:
    def __init__(self, uri, user, password):
        self.driver = _Neo4jDriver.driver(uri, auth=(user, password))
        with self.driver.session() as session:
            session.execute_write(self._run_setup)

    def close(self):
        self.driver.close()

    def _run_setup(self, tx):
        self._setup_trait(tx)

    def _setup_trait(self, tx):
        for name in TRAIT_NODES:
            tx.run("MERGE (:Trait {name: $name})", name=name)
        for name in PRIMARY_EMOTIONS:
            tx.run("MERGE (:Emotion {name: $name, category: 'primary'})", name=name)
        for name, primary in SUB_EMOTIONS:
            tx.run("MERGE (:Emotion {name: $name, category: 'sub'})", name=name)
            tx.run("""
                MATCH (sub:Emotion {name: $sub})
                MATCH (pri:Emotion {name: $pri})
                MERGE (sub)-[:BELONGS_TO]->(pri)
            """, sub=name, pri=primary)

    def save_user(self, user_id, user_info):
        name = user_info.get('name')
        age = user_info.get('age')
        gender = user_info.get('gender')
        now = datetime.now().isoformat()

        query = """
        MERGE (u:User {id: $user_id})
        ON CREATE SET 
            u.name = $name,
            u.age = $age,
            u.gender = $gender,
            u.createdAt = $now,
            u.updatedAt = $now
        ON MATCH SET 
            u.name = CASE WHEN $name IS NOT NULL THEN $name ELSE u.name END,
            u.age = CASE WHEN $age IS NOT NULL THEN $age ELSE u.age END,
            u.gender = CASE WHEN $gender IS NOT NULL THEN $gender ELSE u.gender END,
            u.updatedAt = $now
        RETURN u
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query, 
                                    user_id=user_id, 
                                    name=name, 
                                    age=age, 
                                    gender=gender, 
                                    now=now)
                print(f"User {user_id} saved (created or updated) successfully.")
                return result.single()
            except Exception as e:
                print(f"Error saving user: {e}")
                return None
    
    def update_user_summary(self, user_id, new_summary_text, vector_embedding):
        now = datetime.now().isoformat()

        query = """
        MATCH (u:User {id: $user_id})
        // สร้างหรืออัปเดต Node สรุปข้อมูล
        MERGE (u)-[:HAS_SUMMARY]->(s:UserSummary)
        SET s.text = $text,
            s.embedding = $vector,
            s.updatedAt = $now
        """
        with self.driver.session() as session:
            session.run(query, user_id=user_id, text=new_summary_text, vector=vector_embedding, now=now)

def load():
    global _graph_db
    if _graph_db is None:
        config = get_config()
        _graph_db = GraphDatabase(
            config.GraphDatabase_URI,
            config.GraphDatabase_Username,
            config.GraphDatabase_Password,
        )
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