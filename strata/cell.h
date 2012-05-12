#pragma once

using namespace std;

class cell {
    public:
        int32_t count;
        int8_t counters[32];
        inline cell () {
            count = 0;
            for (int i=0; i<32; i++)
                counters[i] = 0;
        };
        inline cell (const cell &other) {
            count = other.count;
            for (int i=0; i<32; i++) counters[i] = other.counters[i];
        };
        inline cell (const uint32_t &other) {
            count = 1;
            for (int i=0; i<32; i++) counters[i] = (other & (1<<i)) ? 1 : 0;
        };
        inline cell &operator += (const cell &other) {
            count += other.count;
            for (int i=0; i<32; i++) counters[i] += other.counters[i];
            return *this;
        };
        inline cell &operator -= (const cell &other) {
            count -= other.count;
            for (int i=0; i<32; i++) counters[i] -= other.counters[i];
            return *this;
        };
        inline cell &operator *= (const int &other) {
            count *= other;
            for (int i=0; i<32; i++) counters[i] *= other;
            return *this;
        }
        inline cell operator * (const int &other) {
            cell c = cell(*this);
            return (c *= other);
        };
        inline bool isPure() {
            if (count == 0) return false;
            for (int i=0; i<32; i++) if (counters[i] != 0 && counters[i] != count) return false;
            return true;
        };
        inline uint32_t pureValue() {
            uint32_t out = 0;
            for (int i=0; i<32; i++) out |= (counters[i] != 0) ? (1<<i) : 0;
            return out;
        };
        inline bool isZero() {
            if (count != 0) return false;
            for (int i=0; i<32; i++) if (counters[i] != 0) return false;
            return true;
        };
        inline string serialize() {
            return string((const char *)this, sizeof(cell));
        }
        inline size_t deserialize(const char *data) {
            memcpy(this, data, sizeof(cell));
            return sizeof(cell);
        }
};


