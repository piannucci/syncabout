#include "ibf.h"

#include <list>
#include <iostream>
#include <assert.h>

#include "random.h"


using namespace std;

// w = sizeof(uint32_t)
// a uniform odd < 2^w
// b = i << (w/2)
// i uniform < 2^(w/2)
uint32_t hash(uint32_t x, uint32_t a, uint32_t b, uint32_t M) {
    return (a*x+b) >> (8*sizeof(uint32_t) - M);
}

void IBF::init() {
    a = new uint32_t [N];
    b = new uint32_t [N];
    cells = new vector<cell> [N];
    for (int j=0; j<N; j++) {
        a[j] = random32() * 2 + 1;
        b[j] = random32() << 16;
        cells[j].resize(1 << M);
    }
}

IBF::IBF(const IBF &other) {
    N = other.N;
    M = other.M;
    init();
    add_all(other);
}

IBF::IBF(int hashes, int log2_size) {
    N = hashes;
    M = log2_size;
    init();
}

IBF::~IBF () {
    delete [] a;
    delete [] b;
    delete [] cells;
}

void IBF::add(uint32_t x) {
    for (int j=0; j<N; j++) {
        uint32_t h = hash(x, a[j], b[j], M);
        cells[j][h] += x;
    }
}

void IBF::remove(uint32_t x) {
    for (int j=0; j<N; j++) {
        uint32_t h = hash(x, a[j], b[j], M);
        cells[j][h] -= x;
    }
}

bool IBF::test(uint32_t x) {
    for (int j=0; j<N; j++)
        if (cells[j][hash(x, a[j], b[j], M)].isZero())
            return false;
    return true;
}

void IBF::add_all(const set<uint32_t> &other) {
    for (set<uint32_t>::const_iterator i = other.begin(); i!=other.end(); i++)
        add(*i);
}

void IBF::remove_all(const set<uint32_t> &other) {
    for (set<uint32_t>::const_iterator i = other.begin(); i!=other.end(); i++)
        remove(*i);
}

void IBF::add_all(const IBF &other) {
    assert(other.N == N);
    assert(other.M == M);
    for (int j=0; j<N; j++)
        for (uint32_t i=0; i<(1<<M); i++)
            cells[j][i] += other.cells[j][i];
}

void IBF::remove_all(const IBF &other) {
    assert(other.N == N);
    assert(other.M == M);
    for (int j=0; j<N; j++)
        for (uint32_t i=0; i<(1<<M); i++)
            cells[j][i] -= other.cells[j][i];
}

bool IBF::peel(set<uint32_t> &difference) {
    difference.clear();
    list<pair<uint32_t, int> > pure;
    for (uint32_t i=0; i<(1<<M); i++) {
        for (int j=0; j<N; j++) {
            cell &c = cells[j][i];
            if (c.isPure()) {
                pure.push_back(pair<uint32_t, int>(c.pureValue(), c.count));
                break;
            }
        }
    }

    while (!pure.empty()) {
        uint32_t x = pure.front().first;
        pure.pop_front();
        int32_t pureCount = pure.front().second;
        //for (int j=0; j<N; j++) {
        //    uint32_t h = hash(x, a[j], b[j], M);
        //    cell &c = cells[j][h];
        //    if (c.isPure()) {
        //        if (c.pureValue() != x)
        //            cout << "aaa" << endl;
        //        pureCount = c.count;
        //        break;
        //    }
        //}
        //if (!pureCount)
        //    continue;
        for (int j=0; j<N; j++) {
            uint32_t h = hash(x, a[j], b[j], M);
            cell &c = cells[j][h];
            c -= cell(x) * pureCount;
            if (c.isPure())
                pure.push_back(pair<uint32_t, int>(c.pureValue(), c.count));
        }
        difference.insert(x);
    }

    for (int j=0; j<N; j++) {
        for (uint32_t i=0; i<(1<<M); i++) {
            cell &c = cells[j][i];
            if (!c.isZero()) {
                cout << "sad face" << endl;
                cout << c.isPure() << endl;
                //cout << c.count << " " << c.idSum << " " << c.hashSum << endl;
                return false;
            }
        }
    }
    return true;
}

string IBF::serialize() {
    string out;
    out.reserve(N * (1<<M) * sizeof(cell));
    for (int j=0; j<N; j++)
        for (int i=0; i<1<<M; i++)
            out.append(cells[j][i].serialize());
    return out;
}

size_t IBF::deserialize(const char *data) {
    const char *data_orig = data;
    for (int j=0; j<N; j++)
        for (int i=0; i<1<<M; i++)
            data += cells[j][i].deserialize(data);
    return data - data_orig;
}
