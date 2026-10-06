from sentence_transformers import SentenceTransformer
import numpy as np


# Load embedding model once
model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


# Different memory types can naturally produce
# different similarity scores.
MEMORY_THRESHOLDS = {
    "name": 0.35,
    "location": 0.25,
    "favorite_language": 0.35,
    "favorite_food": 0.35,
    "favorite_color": 0.35,
    "workplace": 0.35,
    "occupation": 0.35,
    "hobbies": 0.35,
    "skills": 0.35,
    "education": 0.35,
    "project": 0.35,
    "preference": 0.35
}


def get_embedding(text: str):
    return model.encode(
        text,
        convert_to_numpy=True
    )


def cosine_similarity(vector1, vector2):
    return np.dot(vector1, vector2) / (
        np.linalg.norm(vector1) *
        np.linalg.norm(vector2)
    )


def get_memory_descriptions(memory):
    """
    Create multiple natural-language descriptions
    for a memory.
    """

    descriptions = {
        "name": [
            f"The user's name is {memory.value}.",
            f"The user is called {memory.value}.",
            f"The user's name is {memory.value}."
        ],

        "location": [
            f"The user lives in {memory.value}.",
            f"The user's location is {memory.value}.",
            f"The user's city is {memory.value}.",
            f"The user is from {memory.value}.",
            f"The user stays in {memory.value}."
        ],

        "favorite_language": [
            (
                f"The user's favorite programming "
                f"language is {memory.value}."
            ),
            f"The user codes in {memory.value}.",
            (
                f"The user uses {memory.value} "
                f"for programming."
            )
        ],

        "favorite_food": [
            f"The user's favorite food is {memory.value}.",
            f"The user likes eating {memory.value}.",
            f"The user loves {memory.value}."
        ],

        "favorite_color": [
            f"The user's favorite color is {memory.value}.",
            f"The user likes the color {memory.value}."
        ],

        "workplace": [
            f"The user works at {memory.value}.",
            f"The user's workplace is {memory.value}.",
            f"The user is employed at {memory.value}."
        ],

        "occupation": [
            f"The user's occupation is {memory.value}.",
            f"The user works as {memory.value}.",
            f"The user is a {memory.value}."
        ],

        "hobbies": [
            f"The user's hobbies include {memory.value}.",
            f"The user enjoys {memory.value}.",
            f"The user likes {memory.value} as a hobby."
        ],

        "skills": [
            f"The user has skills in {memory.value}.",
            f"The user is skilled in {memory.value}.",
            f"The user knows {memory.value}."
        ],

        "education": [
            f"The user's education is {memory.value}.",
            f"The user studied {memory.value}.",
            f"The user learned {memory.value}."
        ],

        "project": [
            f"The user's project is {memory.value}.",
            f"The user is working on {memory.value}.",
            f"The user's current project is {memory.value}."
        ],

        "preference": [
            f"The user's preference is {memory.value}.",
            f"The user prefers {memory.value}.",
            f"The user likes {memory.value}."
        ]
    }

    return descriptions.get(
        memory.key,
        [
            f"The user's {memory.key.replace('_', ' ')} "
            f"is {memory.value}."
        ]
    )


def find_relevant_memories(
    user_message: str,
    memories: list,
    threshold: float = 0.35,
    top_k: int = 3
):
    """
    Find memories that are semantically related
    to the user's message.
    """

    if not memories:
        return []

    question_embedding = get_embedding(
        user_message
    )

    relevant_memories = []

    for memory in memories:

        descriptions = get_memory_descriptions(
            memory
        )

        best_score = -1.0

        # Compare the user's question with
        # every description of this memory.
        for description in descriptions:

            memory_embedding = get_embedding(
                description
            )

            score = cosine_similarity(
                question_embedding,
                memory_embedding
            )

            if score > best_score:
                best_score = score

        # Use a memory-specific threshold.
        memory_threshold = MEMORY_THRESHOLDS.get(
            memory.key,
            threshold
        )

        # if best_score >= memory_threshold:

        #     relevant_memories.append({
        #         "key": memory.key,
        #         "value": memory.value,
        #         "score": float(best_score)
        #     })

        if best_score >= memory_threshold:

            print(
                "DEBUG MEMORY MATCH:",
                memory.key,
                "=",
                memory.value,
                "SCORE:",
                best_score,
                "THRESHOLD:",
                memory_threshold
            )

            relevant_memories.append({
                "key": memory.key,
                "value": memory.value,
                "score": float(best_score)
            })
    print(
        "DEBUG RELEVANT MEMORIES:",
        relevant_memories
    )
    # Highest similarity first
    relevant_memories.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # Return only top relevant memories
    return relevant_memories[:top_k]