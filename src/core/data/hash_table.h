#ifndef HASH_TABLE_H
#define HASH_TABLE_H

// https://benhoyt.com/writings/hash-table-in-c/

// Hash table structure: create with ht_create, free with ht_destroy.
#include <stdbool.h>
#include <stddef.h>
typedef struct HashTable HashTable;

// Create hash table and return pointer to it, or NULL if out of memory.
HashTable *HashTable_create(void);

// Free memory allocated for hash table, including allocated keys.
void HashTable_destroy(HashTable *table);

// Get item with given key (NUL-terminated) from hash table. Return
// value (which was set with ht_set), or NULL if key not found.
void *HashTable_get(HashTable *table, const char *key);

// Set item with given key (NUL-terminated) to value (which must not
// be NULL). If not already present in table, key is copied to newly
// allocated memory (keys are freed automatically when ht_destroy is
// called). Return address of copied key, or NULL if out of memory.
const char *HashTable_set(HashTable *table, const char *key, void *value);

// Return number of items in hash table.
size_t HashTable_length(HashTable *table);

// Hash table iterator: create with ht_iterator, iterate with ht_next.
typedef struct {
  const char *key; // current key
  void *value;     // current value

  // Don't use these fields directly.
  HashTable *_table; // reference to hash table being iterated
  size_t _index;     // current index into ht._entries
} HashTableIterator;

// Return new hash table iterator (for use with ht_next).
HashTableIterator HashTable_iterator(HashTable *table);

// Move iterator to next item in hash table, update iterator's key
// and value to current item, and return true. If there are no more
// items, return false. Don't call ht_set during iteration.
bool HashTable_next(HashTableIterator *it);

#endif