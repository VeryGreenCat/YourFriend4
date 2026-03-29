from datetime import datetime

from neo4j import GraphDatabase as _Neo4jDriver

from agent.utils import EMOTIONS, TRAIT_NODES, get_config

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
        self._setup_vector_index(tx)

    def _setup_vector_index(self, tx):
        tx.run(
            """
            CREATE VECTOR INDEX backstory_vector_index IF NOT EXISTS
            FOR (n:BackstoryChunk) ON (n.embedding)
            OPTIONS { indexConfig: {
              `vector.dimensions`: 768,
              `vector.similarity_function`: 'cosine'
            }}
        """
        )

    def _setup_trait(self, tx):
        for name, desc in TRAIT_NODES.items():
            tx.run(
                "MERGE (t:Trait {name: $name}) SET t.description = $desc",
                name=name,
                desc=desc,
            )
        for name, desc in EMOTIONS:
            tx.run(
                "MERGE (e:Emotion {name: $name}) SET e.description = $desc",
                name=name,
                desc=desc,
            )

    def save_user(self, user_id, user_info):
        name = user_info.get("name")
        age = user_info.get("age")
        gender = user_info.get("gender")
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
                result = session.run(
                    query, user_id=user_id, name=name, age=age, gender=gender, now=now
                )
                print(f"User {user_id} saved (created or updated) successfully.")
                return result.single()
            except Exception as e:
                print(f"Error saving user: {e}")
                return None

    def save_bot_profile(self, bot_id, user_id, bot_info):
        name = bot_info.get("name")
        backstory = bot_info.get("backstory")
        now = datetime.now().isoformat()

        query = """
        MERGE (b:Bot {id: $bot_id})
        ON CREATE SET 
            b.name = $name,
            b.backstory = $backstory,
            b.createdAt = $now,
            b.updatedAt = $now
        ON MATCH SET 
            b.name = CASE WHEN $name IS NOT NULL THEN $name ELSE b.name END,
            b.backstory = CASE WHEN $backstory IS NOT NULL THEN $backstory ELSE b.backstory END,
            b.updatedAt = $now
        WITH b
        MATCH (u:User {id: $user_id})
        MERGE (u)-[:OWNS]->(b)
        RETURN b
        """

        with self.driver.session() as session:
            try:
                result = session.run(
                    query,
                    bot_id=bot_id,
                    user_id=user_id,
                    name=name,
                    backstory=backstory,
                    now=now,
                )
                print(f"Bot {bot_id} saved (created or updated) successfully.")
                return result.single()
            except Exception as e:
                print(f"Error saving bot profile: {e}")
                return None

    def get_user_summary(self, user_id):
        query = """
        MATCH (u:User {id: $user_id})-[:HAS_SUMMARY]->(s:UserSummary)
        RETURN s.text AS summary, s.embedding AS embedding
        """
        with self.driver.session() as session:
            result = session.run(query, user_id=user_id)
            record = result.single()
            if record:
                return record["summary"], record["embedding"]
            else:
                return None, None

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
            session.run(
                query,
                user_id=user_id,
                text=new_summary_text,
                vector=vector_embedding,
                now=now,
            )

    # ── Bot ↔ Trait ──────────────────────────────────────────

    def link_bot_trait(self, bot_id, trait_name, weight):
        query = """
        MATCH (b:Bot {id: $bot_id})
        MATCH (t:Trait {name: $trait_name})
        MERGE (b)-[r:HAS_TRAIT]->(t)
        SET r.weight = $weight
        """
        with self.driver.session() as session:
            session.run(query, bot_id=bot_id, trait_name=trait_name, weight=weight)

    def clear_bot_traits(self, bot_id):
        query = """
        MATCH (b:Bot {id: $bot_id})-[r:HAS_TRAIT]->()
        DELETE r
        """
        with self.driver.session() as session:
            session.run(query, bot_id=bot_id)

    # ── Bot ↔ Emotion ────────────────────────────────────────

    def link_bot_emotion(self, bot_id, emotion_name, weight):
        query = """
        MATCH (b:Bot {id: $bot_id})
        MATCH (e:Emotion {name: $emotion_name})
        MERGE (b)-[r:HAS_EMOTION]->(e)
        SET r.weight = $weight
        """
        with self.driver.session() as session:
            session.run(query, bot_id=bot_id, emotion_name=emotion_name, weight=weight)

    def clear_bot_emotions(self, bot_id):
        query = """
        MATCH (b:Bot {id: $bot_id})-[r:HAS_EMOTION]->()
        DELETE r
        """
        with self.driver.session() as session:
            session.run(query, bot_id=bot_id)

    # ── WorldView ────────────────────────────────────────────

    def create_world_view(
        self, bot_id, wv_id, description, affected_traits, reason=None
    ):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (b:Bot {id: $bot_id})
                CREATE (wv:WorldView {id: $wv_id, description: $description})
                CREATE (b)-[:HAS_WORLD_VIEW]->(wv)
            """,
                bot_id=bot_id,
                wv_id=wv_id,
                description=description,
            )

            for trait in affected_traits:
                session.run(
                    """
                    MATCH (wv:WorldView {id: $wv_id})
                    MATCH (t:Trait {name: $trait_name})
                    MERGE (wv)-[r:AFFECTS_TRAIT]->(t)
                    SET r.change_per_second = $rate
                """,
                    wv_id=wv_id,
                    trait_name=trait["name"],
                    rate=trait["change_per_second"],
                )

            if reason:
                session.run(
                    """
                    MATCH (wv:WorldView {id: $wv_id})
                    CREATE (r:Reason {text: $reason})
                    CREATE (wv)-[:HAS_REASON]->(r)
                """,
                    wv_id=wv_id,
                    reason=reason,
                )

    def update_world_view(self, wv_id, description, affected_traits, reason=None):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (wv:WorldView {id: $wv_id})
                SET wv.description = $description
            """,
                wv_id=wv_id,
                description=description,
            )

            session.run(
                """
                MATCH (wv:WorldView {id: $wv_id})-[r:AFFECTS_TRAIT]->()
                DELETE r
            """,
                wv_id=wv_id,
            )

            for trait in affected_traits:
                session.run(
                    """
                    MATCH (wv:WorldView {id: $wv_id})
                    MATCH (t:Trait {name: $trait_name})
                    MERGE (wv)-[r:AFFECTS_TRAIT]->(t)
                    SET r.change_per_second = $rate
                """,
                    wv_id=wv_id,
                    trait_name=trait["name"],
                    rate=trait["change_per_second"],
                )

            session.run(
                """
                MATCH (wv:WorldView {id: $wv_id})-[:HAS_REASON]->(r:Reason)
                DETACH DELETE r
            """,
                wv_id=wv_id,
            )

            if reason:
                session.run(
                    """
                    MATCH (wv:WorldView {id: $wv_id})
                    CREATE (r:Reason {text: $reason})
                    CREATE (wv)-[:HAS_REASON]->(r)
                """,
                    wv_id=wv_id,
                    reason=reason,
                )

    def remove_world_view(self, wv_id):
        query = """
        MATCH (wv:WorldView {id: $wv_id})
        OPTIONAL MATCH (wv)-[:HAS_REASON]->(r:Reason)
        DETACH DELETE wv, r
        """
        with self.driver.session() as session:
            session.run(query, wv_id=wv_id)

    def get_world_views(self, bot_id):
        query = """
        MATCH (b:Bot {id: $bot_id})-[:HAS_WORLD_VIEW]->(wv:WorldView)
        OPTIONAL MATCH (wv)-[at:AFFECTS_TRAIT]->(t:Trait)
        OPTIONAL MATCH (wv)-[:HAS_REASON]->(r:Reason)
        RETURN wv.id AS id, wv.description AS description,
               collect(DISTINCT {name: t.name, change_per_second: at.change_per_second}) AS affected_traits,
               r.text AS reason
        """
        with self.driver.session() as session:
            result = session.run(query, bot_id=bot_id)
            return [dict(record) for record in result]

    def clear_world_views(self, bot_id):
        query = """
        MATCH (b:Bot {id: $bot_id})-[:HAS_WORLD_VIEW]->(wv:WorldView)
        OPTIONAL MATCH (wv)-[:HAS_REASON]->(r:Reason)
        DETACH DELETE wv, r
        """
        with self.driver.session() as session:
            session.run(query, bot_id=bot_id)

    # ── EmotionCondition ─────────────────────────────────────

    def create_emotion_condition(self, bot_id, ec_id, description, reason=None):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (b:Bot {id: $bot_id})
                CREATE (ec:EmotionCondition {id: $ec_id, description: $description})
                CREATE (b)-[:HAS_EMOTION_CONDITION]->(ec)
            """,
                bot_id=bot_id,
                ec_id=ec_id,
                description=description,
            )

            if reason:
                session.run(
                    """
                    MATCH (ec:EmotionCondition {id: $ec_id})
                    CREATE (r:Reason {text: $reason})
                    CREATE (ec)-[:HAS_REASON]->(r)
                """,
                    ec_id=ec_id,
                    reason=reason,
                )

    def update_emotion_condition(self, ec_id, description, reason=None):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (ec:EmotionCondition {id: $ec_id})
                SET ec.description = $description
            """,
                ec_id=ec_id,
                description=description,
            )

            session.run(
                """
                MATCH (ec:EmotionCondition {id: $ec_id})-[:HAS_REASON]->(r:Reason)
                DETACH DELETE r
            """,
                ec_id=ec_id,
            )

            if reason:
                session.run(
                    """
                    MATCH (ec:EmotionCondition {id: $ec_id})
                    CREATE (r:Reason {text: $reason})
                    CREATE (ec)-[:HAS_REASON]->(r)
                """,
                    ec_id=ec_id,
                    reason=reason,
                )

    def remove_emotion_condition(self, ec_id):
        query = """
        MATCH (ec:EmotionCondition {id: $ec_id})
        OPTIONAL MATCH (ec)-[:HAS_REASON]->(r:Reason)
        DETACH DELETE ec, r
        """
        with self.driver.session() as session:
            session.run(query, ec_id=ec_id)

    def get_emotion_conditions(self, bot_id):
        query = """
        MATCH (b:Bot {id: $bot_id})-[:HAS_EMOTION_CONDITION]->(ec:EmotionCondition)
        OPTIONAL MATCH (ec)-[:HAS_REASON]->(r:Reason)
        RETURN ec.id AS id, ec.description AS description, r.text AS reason
        """
        with self.driver.session() as session:
            result = session.run(query, bot_id=bot_id)
            return [dict(record) for record in result]

    def clear_emotion_conditions(self, bot_id):
        query = """
        MATCH (b:Bot {id: $bot_id})-[:HAS_EMOTION_CONDITION]->(ec:EmotionCondition)
        OPTIONAL MATCH (ec)-[:HAS_REASON]->(r:Reason)
        DETACH DELETE ec, r
        """
        with self.driver.session() as session:
            session.run(query, bot_id=bot_id)

    # ── Backstory RAG chunks ─────────────────────────────────

    def save_backstory_chunks(self, bot_id, chunks, embeddings):
        """chunks: list[str], embeddings: list[list[float]]"""
        with self.driver.session() as session:
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                session.run(
                    """
                    CREATE (:BackstoryChunk {
                        id: $id,
                        bot_id: $bot_id,
                        text: $text,
                        embedding: $emb,
                        chunk_index: $idx
                    })
                """,
                    id=f"{bot_id}_{i}",
                    bot_id=bot_id,
                    text=chunk,
                    emb=emb,
                    idx=i,
                )

    def clear_backstory_chunks(self, bot_id):
        query = """
        MATCH (n:BackstoryChunk {bot_id: $bot_id}) DETACH DELETE n
        """
        with self.driver.session() as session:
            session.run(query, bot_id=bot_id)

    def search_backstory(self, bot_id, query_embedding, top_k=4):
        query = """
        CALL db.index.vector.queryNodes(
            'backstory_vector_index', $k, $emb
        ) YIELD node, score
        WHERE node.bot_id = $bot_id
        RETURN node.text AS text, score
        ORDER BY score DESC
        """
        with self.driver.session() as session:
            result = session.run(query, k=top_k, emb=query_embedding, bot_id=bot_id)
            return [r["text"] for r in result]


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
