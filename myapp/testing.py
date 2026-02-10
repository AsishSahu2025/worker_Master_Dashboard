def is_anagram(str1, str2):
    # Normalize the strings: remove spaces, punctuation, convert to lowercase
    str1 = ''.join(e for e in str1 if e.isalnum()).lower()
    print(str1)
    str2 = ''.join(e for e in str2 if e.isalnum()).lower()
    
    # Check if sorted characters of both strings are the same
    return sorted(str1) == sorted(str2)

# Example usage
print(is_anagram("listen", "netsi"))      # Output: True
print(is_anagram("hello", "world"))        # Output: False
print(is_anagram("triangle", "integral"))  # Output: True
print(is_anagram("apple", "pale"))         # Output: False
print(is_anagram("A gentleman", "Elegant man"))  # Output: True
