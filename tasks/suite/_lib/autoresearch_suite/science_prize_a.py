"""Exact, independently authored finite restrictions of 30 prize-bank problems.

No source implementation is reused. See catalog/science/prize_a.json for
mathematical attribution, conventions, resource bounds and scope differences.
"""
from collections import Counter
from fractions import Fraction
from functools import lru_cache
from itertools import combinations, combinations_with_replacement
from math import gcd, isqrt, log

from .runtime import require


def integer(x, lo, hi, name='integer'):
    require(type(x) is int, f'{name} must be a Python int, not bool or float')
    require(lo <= x <= hi, f'{name} must be between {lo} and {hi}')
    return x


def sequence(x, lo, hi, name='sequence'):
    require(type(x) in (list, tuple), f'{name} must be a list or tuple')
    require(lo <= len(x) <= hi, f'{name} must have {lo}..{hi} entries')
    return list(x)


def subset(x, n, minimum=1, maximum=None, lower=1):
    a = sequence(x, minimum, n if maximum is None else maximum, 'set')
    for v in a:
        integer(v, lower, n, 'element')
    require(len(set(a)) == len(a), 'set elements must be distinct')
    return sorted(a)


def result(score, **details):
    return score, {'arithmetic': 'exact integer or rational verification',
                   'lean_verified': False, **details}


def goldbach_decompositions(certificate, start=1000000, count=256):
    rows=sequence(certificate,count,count,'Goldbach pairs')
    sieve=primes(start+2*(count-1))
    solved=0
    for i,row in enumerate(rows):
        if row is None:continue
        target=start+2*i
        pair=sequence(row,2,2,'prime pair')
        a,b=[integer(x,2,target-2,'prime summand') for x in pair]
        require(a+b==target and sieve[a] and sieve[b], 'invalid Goldbach decomposition')
        solved+=1
    require(solved>0,'at least one target must be solved')
    return result(solved/count, solved=solved, total=count, numerator=solved, denominator=count)


def abc_quality(certificate, maximum=10**12):
    row=sequence(certificate,3,3,'abc triple')
    a,b,c=[integer(x,1,maximum,'abc entry') for x in row]
    require(a<=b and a+b==c and gcd(a,b)==1, 'require a<=b, a+b=c and gcd(a,b)=1')
    factors=set()
    for value in (a,b,c):
        d=2
        while d*d<=value:
            if value%d==0:
                factors.add(d)
                while value%d==0:value//=d
            d+=1
        if value>1:factors.add(value)
    radical=1
    for p in factors:radical*=p
    return result(log(c)/log(radical), radical=radical, c=c, prime_factors=sorted(factors),
                  score_serialization='Floating logarithmic quality; equation, coprimality and radical verified exactly')


def hadamard_orders(certificate, maximum=100):
    orders=list(range(4,maximum+1,4))
    rows=sequence(certificate,len(orders),len(orders),'matrices in increasing order')
    solved=[]
    for n,matrix in zip(orders,rows):
        if matrix is None:continue
        matrix=sequence(matrix,n,n,'matrix rows')
        for i,row in enumerate(matrix):
            matrix[i]=sequence(row,n,n,'matrix row')
            require(all(type(x) is int and x in (-1,1) for x in matrix[i]),'matrix entries must be integer signs')
        for a,b in combinations(matrix,2):
            require(sum(x*y for x,y in zip(a,b))==0,'matrix rows are not orthogonal')
        solved.append(n)
    require(solved,'at least one order must be constructed')
    return result(len(solved)/len(orders), solved_orders=solved, numerator=len(solved), denominator=len(orders))


def lonely_runner(certificate, speeds=None, maximum_denominator=1000000):
    speeds=[1,3,4,7,11,18,29] if speeds is None else speeds
    row=sequence(certificate,2,2,'rational time')
    p=integer(row[0],1,maximum_denominator-1,'time numerator')
    q=integer(row[1],2,maximum_denominator,'time denominator')
    require(p<q,'time must be in (0,1)')
    distances=[Fraction(min((p*v)%q,q-(p*v)%q),q) for v in speeds]
    value=min(distances)
    return result(float(value), numerator=value.numerator, denominator=value.denominator,
                  relative_speeds=speeds, time_numerator=p, time_denominator=q,
                  score_serialization='float of exact rational; exact fraction retained')


def egyptian_four(certificate, start=3, count=254, maximum=10**12):
    rows=sequence(certificate,count,count,'three-unit-fraction representations')
    solved=0
    for n,row in zip(range(start,start+count),rows):
        if row is None:continue
        x,y,z=subset(row,maximum,3,3)
        require(4*x*y*z==n*(x*y+x*z+y*z),'unit fractions do not sum to 4/n')
        solved+=1
    require(solved,'at least one target must be solved')
    return result(solved/count, solved=solved,total=count,numerator=solved,denominator=count,
                  distinct_denominators=True)


@lru_cache(maxsize=8)
def primes(n):
    sieve = bytearray(b'\1') * (n + 1)
    sieve[:2] = b'\0\0'
    for p in range(2, isqrt(n) + 1):
        if sieve[p]:
            sieve[p*p:n+1:p] = b'\0' * ((n-p*p)//p+1)
    return bytes(sieve)


def progressions(n, k):
    for d in range(1, (n-1)//(k-1)+1):
        for a in range(1, n-(k-1)*d+1):
            yield tuple(a+i*d for i in range(k))


def distinct_subset_sums(values, n=12, maximum=2**20):
    a = subset(values, maximum, n, n)
    sums = {0}
    for x in a:
        added = {s+x for s in sums}
        require(not sums.intersection(added), 'two distinct subsets have equal sums')
        sums.update(added)
    return result(max(a), subset_count=len(sums))


def harmonic_progression_free(values, n=256, k=3):
    a = subset(values, n)
    selected = set(a)
    require(all(not selected.issuperset(p) for p in progressions(n,k)), 'forbidden progression')
    score = sum((Fraction(1,x) for x in a), Fraction())
    return result(float(score), numerator=score.numerator, denominator=score.denominator, cardinality=len(a), score_serialization='float of exact rational; exact fraction retained')


def property_p(values, n=256):
    a = subset(values, n)
    # The primary papers allow j=k: a_i must not divide 2*a_j either.
    for i,x in enumerate(a):
        require(all((b+c)%x for b,c in combinations_with_replacement(a[i+1:],2)), 'an element divides a sum of two larger elements (repetition allowed)')
    return result(len(a), repeated_larger_elements_allowed=True)


def cluster_prime(value, maximum=100000):
    p = integer(value,3,maximum,'prime')
    sieve = primes(p)
    require(sieve[p], 'candidate is composite')
    ps = [q for q in range(2,p+1) if sieve[q]]
    covered = {q-r for q in ps for r in ps if q>r and (q-r)%2==0}
    required = set(range(2,p-2,2))
    require(required.issubset(covered), 'some required even difference is absent')
    return result(p, differences_verified=len(required))


def practical_divisor_sum(values, n=5040, target=4979):
    a = subset(values,n,maximum=256)
    require(all(n%x==0 for x in a), 'not a divisor of n')
    require(sum(a)==target, 'divisor sum differs from target')
    return result(len(a), target=target, practical_number=n)


def sunflower_free(family, n=16, k=4, petals=3, maximum=250):
    rows = sequence(family,1,maximum,'family')
    masks=[]
    for row in rows:
        a=subset(row,n,k,k)
        masks.append(sum(1<<(x-1) for x in a))
    require(len(set(masks))==len(masks), 'duplicate set')
    require(petals==3, 'only the three-petal profile is implemented')
    for a,b,c in combinations(masks,3):
        require(not(a&b==a&c==b&c), 'three sets form a sunflower (empty core included)')
    return result(len(masks), uniformity=k, ground_set=n)


def bounded_basis(values, n=128):
    a=subset(values,n,maximum=n+1,lower=0)
    counts=Counter(x+y for x,y in combinations_with_replacement(a,2))
    require(all(counts[t]>0 for t in range(n,2*n+1)), 'target interval is not covered')
    return result(max(counts[t] for t in range(n,2*n+1)), cardinality=len(a), interval=[n,2*n], pair_convention='unordered including diagonal')


def prime_complement(values, n=256):
    a=subset(values,n,maximum=n+1,lower=0)
    sieve=primes(2*n)
    require(all(any(t-b>=2 and sieve[t-b] for b in a) for t in range(n,2*n+1)), 'prime-plus-complement misses a target')
    return result(len(a), target_interval=[n,2*n])


def b3_set(values, n=4096, maximum=80):
    a=subset(values,n,maximum=maximum)
    sums=[sum(t) for t in combinations_with_replacement(a,3)]
    require(len(set(sums))==len(sums), 'different unordered triples have the same sum')
    return result(len(a), triple_count=len(sums), repetitions_allowed=True)


def paired_sidon(certificate, n=256):
    pair=sequence(certificate,2,2,'pair of Sidon sets')
    sets=[subset(row,n,maximum=64) for row in pair]
    differences=[]
    for a in sets:
        sums=[x+y for x,y in combinations_with_replacement(a,2)]
        require(len(set(sums))==len(sums), 'a component is not Sidon (diagonals included)')
        differences.append({y-x for x,y in combinations(a,2)})
    require(not differences[0].intersection(differences[1]), 'nonzero difference sets intersect')
    return result(sum(map(len,sets)), component_sizes=list(map(len,sets)))


def sum_product(values, n=20, maximum=10000):
    a=subset(values,maximum,n,n)
    sums={x+y for x in a for y in a}
    products={x*y for x in a for y in a}
    return result(max(len(sums),len(products)), sumset_size=len(sums), product_set_size=len(products))


def antichain_representations(certificate, targets=None, maximum_terms=30):
    targets=list(range(1,129)) if targets is None else targets
    rows=sequence(certificate,len(targets),len(targets),'target representations')
    total_terms=0
    for target,row in zip(targets,rows):
        terms=subset(row,target,maximum=maximum_terms)
        for term in terms:
            remaining=term
            for p in (2,3,5):
                while remaining%p==0:
                    remaining//=p
            require(remaining==1, 'term has a prime factor outside 2,3,5')
        require(sum(terms)==target, 'terms do not sum to target')
        require(all(y%x for x,y in combinations(terms,2)), 'a chosen term divides another')
        total_terms+=len(terms)
    return result(total_terms, solved=len(targets), total=len(targets),
                  local_secondary_objective='Minimize representation length with complete coverage required')


def pair_sum_prime_diversity(values, n=12, maximum=10000):
    a=subset(values,maximum,n,n)
    factors=set()
    for x,y in combinations(a,2):
        v=x+y
        d=2
        while d*d<=v:
            if v%d==0:
                factors.add(d)
                while v%d==0:v//=d
            d+=1
        if v>1:factors.add(v)
    return result(len(factors), prime_factors=sorted(factors), distinct_index_pairs=True)


def nondividing_k_sum(values, n=192, k=3, maximum=48):
    a=subset(values,n,maximum=maximum)
    for i,x in enumerate(a):
        require(all(sum(t)%x for t in combinations(a[:i]+a[i+1:],k)), 'element divides sum of k distinct other elements')
    return result(len(a), subset_size=k, distinct_other_elements=True)


def van_der_waerden(colors, k=4, maximum=512):
    a=sequence(colors,k,maximum,'two-coloring')
    for x in a:integer(x,0,1,'color')
    require(all(len({a[x-1] for x in p})>1 for p in progressions(len(a),k)), 'monochromatic progression')
    return result(len(a), progression_length=k)


def progression_free(values, n=512, k=4):
    a=subset(values,n)
    selected=set(a)
    require(all(not selected.issuperset(p) for p in progressions(n,k)), 'forbidden progression')
    return result(len(a), progression_length=k)


def three_color_progressions(colors, n=128):
    a=sequence(colors,n,n,'coloring')
    for x in a:integer(x,0,n-1,'color')
    require(all(len({a[x-1] for x in p})>=3 for p in progressions(n,4)), 'four-term progression uses fewer than three colors')
    return result(len(set(a)), progression_length=4, minimum_colors_per_progression=3)


def triple_free(values,n=4096):
    a=subset(values,n)
    selected=set(a)
    require(all(not selected.issuperset((x,2*x,3*x)) for x in range(1,n//3+1)), 'contains x,2x,3x')
    return result(len(a), density_numerator=len(a), density_denominator=n)


def progression_discrepancy(signs,n=256):
    a=sequence(signs,n,n,'signs')
    for x in a:
        require(type(x) is int and x in (-1,1), 'each sign must be an integer -1 or +1')
    # Every progression is a contiguous segment of exactly one residue chain.
    best=1
    for d in range(1,n):
        for r in range(d):
            prefix=low=high=0
            for x in a[r::d]:
                prefix+=x
                best=max(best,abs(prefix-low),abs(prefix-high))
                low=min(low,prefix);high=max(high,prefix)
    return result(best, includes_singletons=True, all_starts_and_positive_differences=True)


def many_short_progressions(values,n=256):
    a=subset(values,n)
    selected=set(a)
    require(all(not selected.issuperset(p) for p in progressions(n,4)), 'contains a four-term progression')
    count=sum(selected.issuperset(p) for p in progressions(n,3))
    return result(count, cardinality=len(a), ambient_interval=[1,n])


def nonaveraging(values,n=512,maximum=48):
    a=subset(values,n,maximum=maximum)
    for i,x in enumerate(a):
        others=a[:i]+a[i+1:]
        reachable=[1]+[0]*len(others)
        for j,y in enumerate(others):
            for k in range(j+1,0,-1):
                reachable[k] |= reachable[k-1]<<y
        require(all(not((reachable[k]>>(k*x))&1) for k in range(2,len(others)+1)), 'an element averages a subset of other elements')
    return result(len(a), every_subset_cardinality_checked=True)


def permutation_progression(permutation,n=128):
    a=subset(permutation,n,n,n)
    # subset() sorted only for validating the permutation; retain original order.
    positions=[0]*(n+1)
    for i,x in enumerate(permutation):positions[x]=i
    best=1
    for d in range(1,n):
        increasing=[1]*(n+1);decreasing=[1]*(n+1)
        for x in range(d+1,n+1):
            if positions[x]>positions[x-d]:increasing[x]=increasing[x-d]+1
            else:decreasing[x]=decreasing[x-d]+1
            best=max(best,increasing[x],decreasing[x])
    return result(best, ascending_and_descending_values=True)


def disjoint_congruences(classes,maximum=128):
    rows=sequence(classes,1,maximum,'congruence classes')
    verified=[]
    for row in rows:
        r,m=sequence(row,2,2,'residue/modulus pair')
        m=integer(m,2,maximum,'modulus');r=integer(r,0,m-1,'residue')
        verified.append((r,m))
    require(len({m for r,m in verified})==len(verified),'moduli must be distinct')
    require(all((a-b)%gcd(m,n)!=0 for (a,m),(b,n) in combinations(verified,2)), 'two classes intersect by the Chinese remainder theorem')
    return result(len(rows), modulus_cap=maximum)


def squarefree_gap(endpoints,maximum=10**7,maximum_gap=10000):
    a,b=sequence(endpoints,2,2,'endpoints')
    integer(a,1,maximum-1,'left endpoint');integer(b,a+1,maximum,'right endpoint')
    require(b-a<=maximum_gap,'gap exceeds resource bound')
    def squarefree(x):
        return all(x%(d*d) for d in range(2,isqrt(x)+1))
    require(squarefree(a) and squarefree(b),'both endpoints must be squarefree')
    require(all(not squarefree(x) for x in range(a+1,b)),'a squarefree integer occurs inside')
    return result(b-a,endpoints=[a,b])


def two_square_gap(endpoints,maximum=10**7,maximum_gap=10000):
    a,b=sequence(endpoints,2,2,'endpoints')
    integer(a,1,maximum-1,'left endpoint');integer(b,a+1,maximum,'right endpoint')
    require(b-a<=maximum_gap,'gap exceeds resource bound')
    def representable(x):
        return any(isqrt(x-y*y)**2==x-y*y for y in range(isqrt(x)+1))
    require(representable(a) and representable(b),'endpoints must be sums of two squares (zero allowed)')
    require(all(not representable(x) for x in range(a+1,b)),'a sum of two squares occurs inside')
    return result(b-a,endpoints=[a,b],zero_summands_allowed=True)
