#pragma once

#include <stdint.h>
#include <set>
#include <string>
#include <vector>

#include "cell.h"

class IBF {
    public:
        void add(uint32_t x);
        void remove(uint32_t x);
        IBF(int hashes, int log2_size);
        IBF(const IBF &other);
        ~IBF ();
        void add_all(const std::set<uint32_t> &other);
        void remove_all(const std::set<uint32_t> &other);
        void add_all(const IBF &other);
        void remove_all(const IBF &other);
        bool test(uint32_t x);
        bool peel(std::set<uint32_t> &difference);
        std::string serialize();
        size_t deserialize(const char *data);

    private:
        int N, M;
        std::vector<cell> *cells;
        uint32_t *a, *b;
        void init();
};

