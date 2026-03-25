from neo4j import GraphDatabase
from dataclasses import dataclass
from typing import Any
from utils import get_config

config = get_config()
driver = GraphDatabase.driver(config["GRAPH_DATABASE_URI"], auth=(config["GRAPH_DATABASE_USERNAME"], config["GRAPH_DATABASE_PASSWORD"]))

TRAIT_NODES = [
    "kindness", "aggressiveness", "rationality",
    "emotional_stability", "honesty", "optimism",
    "empathy", "curiosity", "calmness", "carefulness",
    "anxiety",
]

PRIMARY_EMOTIONS = [
    "happiness", "sadness", "fear", "disgust", "anger", "surprise",
]

SUB_EMOTIONS = [
    # (name, belongs_to_primary)
    ("admiration",             "surprise"),
    ("adoration",              "happiness"),
    ("aesthetic_appreciation", "happiness"),
    ("amusement",              "happiness"),
    ("awe",                    "surprise"),
    ("awkwardness",            "disgust"),
    ("boredom",                "disgust"),
    ("calmness",               "happiness"),
    ("confusion",              "surprise"),
    ("craving",                "happiness"),
    ("empathic_pain",          "sadness"),
    ("entrancement",           "surprise"),
    ("excitement",             "happiness"),
    ("horror",                 "fear"),
    ("interest",               "surprise"),
    ("joy",                    "happiness"),
    ("nostalgia",              "sadness"),
    ("relief",                 "happiness"),
    ("romance",                "happiness"),
    ("satisfaction",           "happiness"),
    ("sexual_desire",          "happiness"),
    ("anxiety",                "fear"),
]

# trait บางตัวมี emotion ที่แสดงออกมา
EXPRESSED_AS = [
    ("empathy",    "empathic_pain"),
    ("curiosity",  "interest"),
    ("optimism",   "joy"),
    ("calmness",   "calmness"),
    ("anxiety",    "anxiety"),
]


def setup_graph(tx):
    # สร้าง Trait nodes
    for name in TRAIT_NODES:
        tx.run("MERGE (:Trait {name: $name})", name=name)

    # สร้าง primary Emotion nodes
    for name in PRIMARY_EMOTIONS:
        tx.run("MERGE (:Emotion {name: $name, category: 'primary'})", name=name)

    # สร้าง sub Emotion nodes + BELONGS_TO
    for name, primary in SUB_EMOTIONS:
        tx.run("MERGE (:Emotion {name: $name, category: 'sub'})", name=name)
        tx.run("""
            MATCH (sub:Emotion {name: $sub})
            MATCH (pri:Emotion {name: $pri})
            MERGE (sub)-[:BELONGS_TO]->(pri)
        """, sub=name, pri=primary)

    # EXPRESSED_AS: Trait → Emotion
    for trait, emotion in EXPRESSED_AS:
        tx.run("""
            MATCH (t:Trait {name: $trait})
            MATCH (e:Emotion {name: $emotion})
            MERGE (t)-[:EXPRESSED_AS]->(e)
        """, trait=trait, emotion=emotion)


with driver.session() as session:
    session.execute_write(setup_graph)
    print("setup done")


# ─────────────────────────────────────────
# STEP 2: สร้าง character (ทุกครั้งที่มีตัวใหม่)
# ─────────────────────────────────────────

@dataclass
class ConditionalTrait:
    id: str
    trait: str
    delta: float
    description: str
    condition_type: str   # context | emotion | relationship
    condition_key: str
    condition_op: str     # eq | gt | lt | gte | lte
    condition_value: Any


def create_character(tx, character_id: str, name: str,
                     trait_scores: dict,
                     emotion_scores: dict,
                     conditionals: list[ConditionalTrait]):

    # Character node
    tx.run("""
        MERGE (c:Character {id: $id})
        SET c.name = $name
    """, id=character_id, name=name)

    # HAS_TRAIT (ค่าอยู่บน relationship)
    for trait_name, value in trait_scores.items():
        tx.run("""
            MATCH (c:Character {id: $cid})
            MATCH (t:Trait {name: $trait})
            MERGE (c)-[r:HAS_TRAIT]->(t)
            SET r.base_value = $value, r.current_value = $value
        """, cid=character_id, trait=trait_name, value=value)

    # HAS_EMOTION (ค่าอยู่บน relationship)
    for emotion_name, value in emotion_scores.items():
        tx.run("""
            MATCH (c:Character {id: $cid})
            MATCH (e:Emotion {name: $emotion})
            MERGE (c)-[r:HAS_EMOTION]->(e)
            SET r.current_value = $value
        """, cid=character_id, emotion=emotion_name, value=value)

    # ConditionalTrait + Condition + MODIFIES
    for ct in conditionals:
        tx.run("""
            MATCH (c:Character {id: $cid})
            MATCH (t:Trait {name: $trait})

            CREATE (ct:ConditionalTrait {
                id: $ct_id,
                delta: $delta,
                description: $description
            })
            CREATE (cond:Condition {
                type: $ctype,
                key: $ckey,
                op: $cop,
                value: $cval
            })

            CREATE (c)-[:HAS_CONDITIONAL_TRAIT]->(ct)
            CREATE (ct)-[:MODIFIES]->(t)
            CREATE (ct)-[:REQUIRES_CONDITION]->(cond)
        """,
            cid=character_id,
            trait=ct.trait,
            ct_id=ct.id,
            delta=ct.delta,
            description=ct.description,
            ctype=ct.condition_type,
            ckey=ct.condition_key,
            cop=ct.condition_op,
            cval=str(ct.condition_value),
        )


# ─────────────────────────────────────────
# ใช้งานจริง: เรียกหลัง TraitsModel คืนค่า
# ─────────────────────────────────────────

trait_scores  = traits_model("Aria เป็นคนใจดี ช่างสังเกต แต่ไม่ค่อยระวังตัว")
emotion_scores = {"happiness": 0.4, "anxiety": 0.3}

conditionals = [
    ConditionalTrait(
        id="ct_alone_careless",
        trait="carefulness", delta=-0.4,
        description="ไม่ระวังตัวเวลาอยู่คนเดียว",
        condition_type="context", condition_key="is_alone",
        condition_op="eq", condition_value=True
    ),
    ConditionalTrait(
        id="ct_angry_honest",
        trait="honesty", delta=0.3,
        description="พูดตรงขึ้นเวลาโกรธ",
        condition_type="emotion", condition_key="anger",
        condition_op="gt", condition_value=0.7
    ),
]

with driver.session() as session:
    session.execute_write(
        create_character,
        "char_001", "Aria",
        trait_scores, emotion_scores, conditionals
    )