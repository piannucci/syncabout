#include <cstdlib>
#include <iostream>
#include <algorithm>
#include <iomanip>
#include <string>
#include <set>
#include <list>
#include <map>
#include <vector>
#include <assert.h>
#include <stdint.h>
#include "random.h"

using namespace std;

// w = sizeof(uint32_t)
// a uniform odd < 2^w
// b = i << (w/2)
// i uniform < 2^(w/2)
uint32_t hash(uint32_t x, uint32_t a, uint32_t b, uint32_t M) {
    return (a*x+b) >> (8*sizeof(uint32_t) - M);
}

const uint32_t hashSumA = 3105878623, hashSumB = 2581856256, hashSumM = 16;

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

class IBF {
    public:
        void add(uint32_t x);
        void remove(uint32_t x);
        IBF(int hashes, int log2_size);
        IBF(const IBF &other);
        ~IBF ();
        void add_all(const set<uint32_t> &other);
        void remove_all(const set<uint32_t> &other);
        void add_all(const IBF &other);
        void remove_all(const IBF &other);
        bool test(uint32_t x);
        bool peel(set<uint32_t> &difference);
        string serialize();
        size_t deserialize(const char *data);

    private:
        int N, M;
        vector<cell> *cells;
        uint32_t *a, *b;
        void init();
};

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

int stratumForKey(uint32_t key) {
    int trailing_ones = 0;
    while (key & 1) {
        key >>= 1;
        trailing_ones++;
    }
    return trailing_ones;
}

const int strataLevels = 32;
const int strataN = 4;
const int strataM = 5;

string encodeStrataEstimator(const set<uint32_t> &s) {
    string out;
    IBF *filters[strataLevels];
    for (int l=0; l<strataLevels; l++)
        filters[l] = new IBF(strataN, strataM);
    for (set<uint32_t>::const_iterator i = s.begin(); i!=s.end(); i++) {
        uint32_t x = *i;
        int l = stratumForKey(x);
        if (l < strataLevels)
            filters[l]->add(x);
    }
    out.reserve(strataN * (1<<strataM) * sizeof(cell) * strataLevels);
    for (int l=0; l<strataLevels; l++) {
        out.append(filters[l]->serialize());
        delete filters[l];
    }
    return out;
}

int decodeStrataEstimator(string estimator, const set<uint32_t> &s) {
    string out;
    IBF *filters[strataLevels];
    const char *data = estimator.data();
    for (int l=0; l<strataLevels; l++) {
        filters[l] = new IBF(strataN, strataM);
        data += filters[l]->deserialize(data);
    }
    for (set<uint32_t>::const_iterator i = s.begin(); i!=s.end(); i++) {
        uint32_t x = *i;
        int l = stratumForKey(x);
        if (l < strataLevels)
            filters[l]->remove(x);
    }
    uint32_t count = 0;
    set<uint32_t> items;
    for (int l=strataLevels; l>=0; l--) {
        if (!filters[l]->peel(items)) {
            cout << "Joy! " << count << endl;
            return count << (l+1);
        }
        count += items.size();
    }
    return count;
}

int main(void) {
    //srandomdev();
    IBF ibf(4, 10);
    vector<bool> values;
    vector<uint32_t> all_values;
    int N = 10000000;   // key space
    int M = 100000;     // keys
    int L = 100;        // keys modified
    values.resize(N);
    // add M unique keys in the range 0...N-1
    for (int i=0; i<M; i++) {
        uint32_t x;
        do {
            x = irand(N);
        } while (values[x]);
        ibf.add(x);
        values[x] = true;
        all_values.push_back(x);
    }

    set<uint32_t> value_set = set<uint32_t>(all_values.begin(), all_values.end());
    set<uint32_t> value_set_2 = set<uint32_t>(value_set);
    string strataEstimator = encodeStrataEstimator(value_set);
    cout << "estimator size: " << strataEstimator.size() << endl;

    vector<uint32_t> added_values;
    vector<uint32_t> removed_values;
    IBF ibf2(ibf);
    for (int i=0; i<L; i++) {
        if (drand() > .5) {
            uint32_t x = irand(N);
            ibf.add(x);
            added_values.push_back(x);
            value_set_2.insert(x);
        } else {
            uint32_t x = all_values[i];
            ibf.remove(x);
            removed_values.push_back(x);
            value_set_2.erase(x);
        }
    }

    int differenceEstimate = decodeStrataEstimator(strataEstimator, value_set_2);

    ibf.remove_all(ibf2);
    set<uint32_t> difference;
    cout << "Peel: " << ibf.peel(difference) << endl;
    int difference_size = difference.size();
    int added_found = 0, added_size = added_values.size();
    int removed_found = 0, removed_size = removed_values.size();
    int bogus_found = 0;
    for (set<uint32_t>::iterator i = difference.begin(); i!= difference.end(); i++) {
        if (find(added_values.begin(), added_values.end(), *i) != added_values.end())
            added_found++;
        else if (find(removed_values.begin(), removed_values.end(), *i) != removed_values.end())
            removed_found++;
        else
            bogus_found++;
    }

    cout << "Found added items: " << added_found << "/" << added_size << endl;
    cout << "Found removed items: " << removed_found << "/" << removed_size << endl;
    cout << "Found bogus items: " << bogus_found << endl;
    cout << "Estimated " << differenceEstimate << "; recovered " << difference_size << "; actual " << L << endl;

    if (0) {
        int results[2][2] = {{0,0},{0,0}};
        for (uint32_t i=0; i<N; i++) {
            bool test = ibf.test(i);
            bool truth = values[i];
            results[truth][test]++;
        }
        cout << "           Pos     Neg" << endl;
        cout << "True  " << setw(8) << results[1][1] << setw(8) << results[1][0] << endl;
        cout << "False " << setw(8) << results[0][1] << setw(8) << results[0][0] << endl;
        cout << added_values.size() << " " << removed_values.size() << endl;
    }

    return 0;
}
