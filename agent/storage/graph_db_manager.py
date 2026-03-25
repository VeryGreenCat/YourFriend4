from utils import get_config
from neo4j import GraphDatabase

cfg = get_config()

URI = cfg.GraphDatabase_URI
AUTH = (cfg.GraphDatabase_Username, cfg.GraphDatabase_Password)

with GraphDatabase.driver(URI, auth=AUTH) as driver:
    driver.verify_connectivity()

def insert_data(tx):
    tx.run("""
    MERGE (u:User {name: 'Alice'})
    MERGE (p:Product {name: 'Laptop'})
    MERGE (u)-[:BOUGHT]->(p)
    """)

with driver.session() as session:
    session.execute_write(insert_data)

def get_context(tx, question):
    result = tx.run("""
    MATCH (u:User)-[:BOUGHT]->(p:Product)
    RETURN u.name AS user, p.name AS product
    LIMIT 10
    """)
    
    data = []
    for record in result:
        data.append(f"{record['user']} bought {record['product']}")
    
    return "\n".join(data)

with driver.session() as session:
    context = session.execute_read(get_context, "Who bought what?")

# from openai import OpenAI
client = OpenAI()

prompt = f"""
Context:
{context}

Question: Who bought what?
Answer:
"""

response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[{"role": "user", "content": prompt}]
)

print(response.choices[0].message.content)


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