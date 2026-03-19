# Assignment 1 - Part B

import sys

"""
Reads a text file and returns a list of tokens.
    
Runtime Complexity: O(n) where n is the number of characters in the file.
"""
def tokenize(file_path):
    tokens = []
    current_token = ""
    
    try:
        file = open(file_path, 'r', encoding='utf-8')
        text = file.read()
        file.close()
        
        for char in text:
            if char.isalnum():
                current_token = current_token + char.lower()
            else:
                if current_token != "":
                    tokens.append(current_token)
                    current_token = ""
        
        if current_token != "":
            tokens.append(current_token)
            
    except Exception as error:
        print("Error: Could not read file")
        print("Details:", error)
        sys.exit(1)
    
    return tokens

"""
Converts a list of tokens to a set of unique tokens.
    
Runtime Complexity: O(n) where n is the number of tokens.
Converting a list to a set requires examining each token once.
"""
def get_unique_tokens(token_list):
    unique_tokens = set()
    
    for token in token_list:
        unique_tokens.add(token)
    
    return unique_tokens

"""
Counts the number of tokens that appear in both sets.
    
Runtime Complexity: O(min(m, n)) where m and n are the sizes of the two sets.
Set intersection operation iterates through the smaller set and checks membership in the larger set.
"""
def count_common_tokens(tokens_set1, tokens_set2):
    common = tokens_set1.intersection(tokens_set2)
    return len(common)

"""
Main function.
    
Runtime Complexity: O(n + m) where n and m are the total characters in file1 and file2.
- Tokenizing file1: O(n)
- Tokenizing file2: O(m)
- Converting to sets: O(tokens in file1) + O(tokens in file2)
"""
def main():
    if len(sys.argv) != 3:
        print("Usage: python PartB.py <file1> <file2>")
        sys.exit(1)
    
    file1_path = sys.argv[1]
    file2_path = sys.argv[2]
    
    # Tokenize both files
    tokens1 = tokenize(file1_path)
    tokens2 = tokenize(file2_path)
    
    # Get unique tokens from each file
    unique_tokens1 = get_unique_tokens(tokens1)
    unique_tokens2 = get_unique_tokens(tokens2)
    
    # Count common tokens
    common_count = count_common_tokens(unique_tokens1, unique_tokens2)
    
    # Print only the number (required by assignment)
    print(common_count)


if __name__ == "__main__":
    main()