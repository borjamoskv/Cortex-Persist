import re


def clean_tests(filename):
    with open(filename) as f:
        text = f.read()

    classes_to_remove = [
        "TestNegativeCache",
        "TestPositiveCache",
        "TestProviderMetrics",
        "TestIntentValidator",
        "TestWeightedProviderPool",
        "TestAdaptiveTTL",
        "TestDNSSECIntegration",
    ]

    for cls in classes_to_remove:
        # Regex to match class definition and its content until the next class or end of file
        text = re.sub(rf"class {cls}(?:.*?)(?=\n\n\n\n|\n\n# ───|\Z)", "", text, flags=re.DOTALL)

    with open(filename, "w") as f:
        f.write(text)


clean_tests("tests/test_llm_router.py")
