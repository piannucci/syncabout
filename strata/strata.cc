#include <cstdlib>
#include <iostream>
#include <algorithm>
#include <iomanip>
#include <string>
#include <set>
#include <vector>
#include <stdint.h>
#include "random.h"
#include "cell.h"
#include "ibf.h"

using namespace std;

const uint32_t hashSumA = 3105878623, hashSumB = 2581856256, hashSumM = 16;

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
