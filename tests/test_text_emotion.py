from agent.models.predict_text_model import predict_text_emotion

TEST_CASES = [
    "I am so happy today, everything is going great!",
    "I hate this, nothing ever works.",
    "I'm not sure how I feel about this...",
    "I can't believe you did that! That's amazing!",
    "I'm so tired and sad, I just want to sleep.",
    "This is fine I guess.",
    "I love spending time with my friends!",
    "I'm really scared about the test tomorrow.",
]


def _normalize_results(results):
    if results and isinstance(results[0], list):
        return results[0]
    return results


def _format_results(results):
    normalized = _normalize_results(results)
    if not normalized:
        return "-"
    return ", ".join(
        f"{item['label']} ({item['score']:.3f})" for item in normalized
    )


def run_tests():
    print(f"{'Input':<50} {'Top emotion':<20} {'Confidence':>10}  All top-k")
    print("-" * 120)
    for text in TEST_CASES:
        results = _normalize_results(predict_text_emotion(text))
        top = results[0]
        rest = _format_results(results[1:])
        print(
            f"{text[:48]:<50} {top['label']:<20} {top['score']:>10.4f}  {rest}"
        )


if __name__ == "__main__":
    run_tests()
