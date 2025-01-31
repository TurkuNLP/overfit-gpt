import argparse

from datasets import load_dataset
from transformers import AutoTokenizer, pipeline, set_seed

parser = argparse.ArgumentParser()
parser.add_argument('--model', help='Model to use')
parser.add_argument('--tokenizer', help='Tokenizer to use')
args = parser.parse_args()
tokenizer = AutoTokenizer.from_pretrained(args.tokenizer)
generator = pipeline('text-generation', model=args.model)
wiki = load_dataset("graelo/wikipedia", "20230601.fi")

set_seed(0)


# Collect samples from the last {n}% of the dataset & cut them to {m} tokens
def collect_data(dataset: dict) -> list:
    print(f"Full dataset: {len(dataset)}", flush=True)
    num_samples = int(0.05 * len(dataset))
    samples = dataset["text"][-num_samples:]
    print(f"Split dataset: {len(samples)}", flush=True)
    splits = []
    for sample in samples:
        splitted = split_text(sample)
        splits.append(splitted)
    return splits


def split_text(text: str,
               max_chunk_length: int = 500,
               include_partials: bool = False
               ) -> list:
    # Tokenize the input text
    tokens = tokenizer.encode(text, add_special_tokens=False)

    # Initialize variables to keep track of chunks
    chunks = []
    current_chunk = []
    current_length = 0

    for token in tokens:
        current_chunk.append(token)
        current_length += 1

        if current_length >= max_chunk_length:
            chunks.append(current_chunk)
            current_chunk = []
            current_length = 0

    # Append the last chunk if it's not empty
    if current_chunk and include_partials:
        chunks.append(current_chunk)

    # Decode each chunk back into text
    chunked_text = [tokenizer.decode(
        chunk, skip_special_tokens=True) for chunk in chunks]

    return chunked_text


def flatten(matrix: list) -> list:
    flat_list = []
    for row in matrix:
        flat_list += row
    return flat_list


# Loop through these examples and use `len-50` as prompt and predict 50 tokens
def predict(data: list) -> tuple[int, int]:
    total = len(data)
    correct = 0
    for sample in data:
        splitted = split_text(sample, 499, True)
        if len(splitted) != 2:
            continue
        prompt = splitted[0]
        truth = splitted[1]
        prediction = generator(prompt, max_new_tokens=1, return_full_text=False)[
            0]['generated_text']
        if score(prediction, truth):
            correct += 1
    return total, correct


# If the model correctly predicts the 50 tokens we give score 1, otherwise 0
def score(prediction: str, truth: str) -> bool:
    return prediction == truth


# Average the score over all examples
def average(total: int, correct: int) -> float:
    fraction = correct/total
    return fraction


def main():
    print(F"Model: {args.model}", flush=True)
    print(F"Tokenizer: {args.tokenizer}", flush=True)
    data = collect_data(wiki["train"])
    flattened = flatten(data)
    print(F"Num samples: {len(flattened)}", flush=True)
    total, correct = predict(flattened)
    final_score = average(total, correct)
    print(f"Fraction extractable: {final_score}")


if __name__ == "__main__":
    main()
