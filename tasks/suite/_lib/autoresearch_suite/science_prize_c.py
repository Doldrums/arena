"""Independent exact finite verifiers for 29 prize-bank research problems.

Definitions, papers, scope changes and mathematical construction credit are in
catalog/science/prize_c.json. No upstream implementation is imported.
"""
from collections import deque
from fractions import Fraction
from functools import lru_cache
from itertools import combinations, product
from math import gcd, isqrt, prod
from .runtime import require


def integer(x, lo, hi, name='integer'):
    require(type(x) is int, name + ' must be a Python int, not bool/float')
    require(lo <= x <= hi, name + ' outside allowed bounds')
    return x


def sequence(x, lo, hi, name='sequence'):
    require(type(x) in (list, tuple), name + ' must be a list or tuple')
    require(lo <= len(x) <= hi, name + ' has invalid length')
    return x


def unique_ints(x, lo, hi, minimum=0, maximum=None, name='vertices'):
    x = sequence(x, minimum, hi-lo+1 if maximum is None else maximum, name)
    out = [integer(a, lo, hi, name) for a in x]
    require(len(set(out)) == len(out), name + ' must be distinct')
    return out


def dictionary(x, keys):
    require(type(x) is dict and set(x) == set(keys), 'certificate has incorrect fields')
    return x


def edges(x, n):
    out = set()
    for row in sequence(x, 0, n*(n-1)//2, 'edges'):
        a,b = sequence(row,2,2,'edge')
        a,b = integer(a,0,n-1),integer(b,0,n-1)
        require(a != b, 'loops are forbidden')
        e = tuple(sorted((a,b)))
        require(e not in out, 'duplicate undirected edge')
        out.add(e)
    return out


def adjacency(es,n):
    a=[set() for _ in range(n)]
    for u,v in es: a[u].add(v); a[v].add(u)
    return a


def hyperedges(x,n,r,minimum=0):
    out=[]
    for row in sequence(x,minimum,1000,'hyperedges'):
        out.append(frozenset(unique_ints(row,0,n-1,r,r,'hyperedge')))
    require(len(set(out))==len(out),'duplicate hyperedges')
    return out


def diameter(a):
    result=0
    for root in range(len(a)):
        distances={root:0}; q=deque([root])
        while q:
            u=q.popleft()
            for v in a[u]:
                if v not in distances: distances[v]=distances[u]+1; q.append(v)
        if len(distances)!=len(a): return None
        result=max(result,max(distances.values()))
    return result


def cycle_lengths(a):
    """All simple cycle lengths; smallest vertex and orientation remove repeats."""
    found=set(); n=len(a)
    def walk(root,path,seen):
        u=path[-1]
        if len(path)>=3 and root in a[u] and path[1]<u: found.add(len(path))
        for v in a[u]:
            if v>root and v not in seen: walk(root,path+[v],seen|{v})
    for root in range(n): walk(root,[root],{root})
    return found


def homogeneous_partition(x,p):
    n=p['n']; es=edges(p['edges'],n)
    rows=sequence(x,1,n,'partition'); seen=set()
    for row in rows:
        row=unique_ints(row,0,n-1,1,n)
        require(not seen.intersection(row),'partition parts overlap'); seen.update(row)
        pair_edges=[tuple(sorted(e)) in es for e in combinations(row,2)]
        require(all(pair_edges) or not any(pair_edges),'part is neither clique nor independent')
    require(seen==set(range(n)),'partition does not cover host vertices')
    # Exact chromatic number is context, not the candidate's claimed value.
    return len(rows), {'chromatic_number':chromatic_number(es,n), 'parts':len(rows)}


def chromatic_number(es,n):
    require(n<=18,'exact chromatic context limited to 18 vertices')
    adj=[0]*n
    for u,v in es: adj[u]|=1<<v;adj[v]|=1<<u
    independent=[False]*(1<<n); independent[0]=True
    for s in range(1,1<<n):
        b=s&-s; rest=s^b; independent[s]=independent[rest] and not(adj[b.bit_length()-1]&rest)
    @lru_cache(None)
    def solve(s):
        if independent[s]: return int(s!=0)
        b=s&-s; answer=n; sub=s
        while sub:
            if sub&b and independent[sub]: answer=min(answer,1+solve(s^sub))
            sub=(sub-1)&s
        return answer
    return solve((1<<n)-1)


def augment_diameter(x,p):
    n=p['n']; base=edges(p['edges'],n); added=edges(x,n)
    require(not(base&added),'output contains an existing edge')
    a=adjacency(base|added,n)
    require(all(not(a[u]&a[v]) for u,v in base|added),'augmentation creates triangle')
    d=diameter(a); require(d is not None and d<=p['diameter'],'diameter too large or disconnected')
    return len(added),{'diameter':d,'added_edges':len(added)}


def degree_diversity(x,p):
    n=p['n']; es=edges(p['edges'],n); a=adjacency(es,n)
    # Re-check the documented Ramsey condition of the fixed host.
    for row in combinations(range(n),p['homogeneous_cap']):
        hits=sum(v in a[u] for u,v in combinations(row,2))
        require(0<hits<len(row)*(len(row)-1)//2,'host violates Ramsey restriction')
    vertices=set(unique_ints(x,0,n-1,p['minimum_vertices'],n))
    counts=sorted({len(a[u]&vertices) for u in vertices})
    return len(counts),{'degree_values':counts,'selected_vertices':len(vertices)}


def common_cycles(x,p):
    n=p['n']; es=edges(p['edges'],n); used=set(); common=None
    rows=sequence(x,1,n//2,'cycles')
    for row in rows:
        row=unique_ints(row,0,n-1,3,n,'cycle')
        if common is None: common=set(row)
        require(set(row)==common,'cycles must have identical vertex sets')
        for u,v in zip(row,row[1:]+row[:1]):
            e=tuple(sorted((u,v)))
            require(e in es and e not in used,'missing or reused cycle edge');used.add(e)
    return len(rows),{'common_vertices':len(common),'used_edges':len(used)}


def no_singleton_intersection(x,p):
    rows=hyperedges(x,p['n'],p['r'],1)
    require(all(len(a&b)!=1 for a,b in combinations(rows,2)),'singleton intersection')
    return len(rows),{'uniformity':p['r'],'vertices':p['n']}


def matching_window(n,start):
    """Compute f(n,start) exactly by augmenting paths at each prefix length."""
    integer(n,1,30); integer(start,0,10**9)
    def possible(length):
        choices={d:list(range((start//d+1)*d,start+length+1,d)) for d in range(1,n+1)}
        owner={}
        def augment(d,seen):
            for value in choices[d]:
                if value in seen: continue
                seen.add(value)
                if value not in owner or augment(owner[value],seen): owner[value]=d; return True
            return False
        return all(augment(d,set()) for d in range(n,0,-1))
    # In any n^2 consecutive integers each d<=n has >=n multiples,
    # so Hall's condition holds. Binary search is exact by monotonicity.
    low,high=0,n*n
    while high-low>1:
        mid=(low+high)//2
        if possible(mid): high=mid
        else: low=mid
    return high


def worst_matching_start(x,p):
    start=integer(x,0,p['maximum_start'],'interval start')
    value=matching_window(p['n'],start)
    return value,{'start':start,'least_inclusive_window_length':value}


def clique_subdivision(x,p):
    dictionary(x,('branches','paths'));n=p['n'];es=edges(p['edges'],n)
    branches=unique_ints(x['branches'],0,n-1,2,n); bset=set(branches)
    paths=sequence(x['paths'],len(branches)*(len(branches)-1)//2,len(branches)*(len(branches)-1)//2,'paths')
    pairs=set();internal=set()
    for path in paths:
        path=unique_ints(path,0,n-1,2,n,'path')
        pair=tuple(sorted((path[0],path[-1])))
        require(set(pair)<=bset and pair not in pairs,'branch pair missing or duplicated'); pairs.add(pair)
        middle=set(path[1:-1]); require(not(middle&bset or middle&internal),'path interiors must be disjoint and avoid branches');internal|=middle
        require(all(tuple(sorted(e)) in es for e in zip(path,path[1:])),'path uses nonedge')
    require(pairs==set(combinations(sorted(branches),2)),'not all branch pairs linked')
    return len(branches),{'internal_vertices':len(internal),'paths':len(paths)}


def mols(x,p):
    n=p['n']; squares=sequence(x,1,n-1,'squares'); norm=[]
    for square in squares:
        rows=sequence(square,n,n,'square')
        rows=[unique_ints(row,0,n-1,n,n,'Latin row') for row in rows]
        require(all(len({rows[i][j] for i in range(n)})==n for j in range(n)),'repeated column symbol');norm.append(rows)
    for a,b in combinations(norm,2):
        require(len({(a[i][j],b[i][j]) for i in range(n) for j in range(n)})==n*n,'squares not orthogonal')
    return len(norm),{'order':n,'orthogonal_pairs':len(norm)*(len(norm)-1)//2}


def hamilton_arrival(x,p):
    n=p['n']; cycle=unique_ints(x,0,n-1,n,n,'Hamilton cycle')
    arrivals={tuple(sorted(e)):i+1 for i,e in enumerate(p['edge_order'])}
    require(len(arrivals)==n*(n-1)//2,'invalid pinned edge process')
    value=max(arrivals[tuple(sorted(e))] for e in zip(cycle,cycle[1:]+cycle[:1]))
    return value,{'certified_prefix':value,'cycle_vertices':n,'proves_earliest_prefix':False}


def matching_arrival(x,p):
    n=p['n']; rows=hyperedges(x,n,3);require(len(rows)==n//3,'wrong number of matching edges')
    used=set()
    for row in rows: require(not used&row,'matching overlaps');used|=row
    require(used==set(range(n)),'matching omits vertices')
    arrivals={frozenset(e):i+1 for i,e in enumerate(p['edge_order'])}
    require(all(e in arrivals for e in rows),'matching edge absent from process')
    value=max(arrivals[e] for e in rows)
    return value,{'certified_prefix':value,'matching_edges':len(rows),'proves_earliest_prefix':False}


def few_cycle_lengths(x,p):
    n=p['n'];require(n<=12,'cycle enumeration capped at 12 vertices');es=edges(x,n);a=adjacency(es,n)
    require(min(map(len,a))>=p['minimum_degree'],'minimum degree too small')
    # The pinned girth-four contract rejects dense invalid graphs before
    # expensive cycle enumeration. Every accepted graph is triangle-free.
    if p['girth']>=4:
        require(all(not a[u]&a[v] for u,v in es),'girth too small: triangle')
    lengths=cycle_lengths(a)
    require(lengths and min(lengths)>=p['girth'],'girth too small')
    return len(lengths),{'cycle_lengths':sorted(lengths),'girth':min(lengths),'edges':len(es)}


def comparable_pairs(x,p):
    rows=sequence(x,p['m'],p['m'],'family')
    rows=[frozenset(unique_ints(row,0,p['n']-1)) for row in rows]
    require(len(set(rows))==len(rows),'duplicate sets')
    value=sum(a<b or b<a for a,b in combinations(rows,2))
    return value,{'sets':len(rows),'ground_set':p['n']}


def two_primitive(x,p):
    values=unique_ints(x,2,p['n'],1,p['n']-1,'integers')
    for a in values:
        others=[b for b in values if b!=a]
        require(all(b*c%a for b,c in combinations(others,2)),'element divides product of two distinct others')
    return len(values),{'three_elements_distinct':True}


def distinct_products(x,p):
    values=unique_ints(x,2,p['n'],1,p['maximum_size'],'integers'); products={1}
    for a in values:
        added={a*v for v in products}
        require(not(products&added),'two distinct subsets have equal products')
        products.update(added)
    return len(values),{'subset_products_including_empty':len(products)}


def acyclic_colors(x,p):
    n=p['n']; colors=[integer(c,0,n-1,'color') for c in sequence(x,n,n,'colors')]
    es=edges(p['edges'],n);require(all(colors[u]!=colors[v] for u,v in es),'coloring is not proper')
    groups={}
    for u,v in es:groups.setdefault(tuple(sorted((colors[u],colors[v]))),[]).append((u,v))
    for group in groups.values():
        parent=list(range(n))
        def find(u):
            while parent[u]!=u:parent[u]=parent[parent[u]];u=parent[u]
            return u
        for u,v in group:
            u,v=find(u),find(v);require(u!=v,'two-colored cycle');parent[u]=v
    return len(set(colors)),{'color_classes':len(set(colors)),'maximum_degree':max(map(len,adjacency(es,n)))}


def biclique_partition(x,p):
    n=p['n']; es=edges(p['edges'],n);used=set();rows=sequence(x,1,len(es),'bicliques')
    for row in rows:
        left,right=sequence(row,2,2,'biclique sides')
        left=unique_ints(left,0,n-1,1,n);right=unique_ints(right,0,n-1,1,n)
        require(not set(left)&set(right),'biclique sides overlap')
        for u in left:
            for v in right:
                e=tuple(sorted((u,v)));require(e in es and e not in used,'nonedge or repeated covered edge');used.add(e)
    require(used==es,'not every host edge is covered')
    return len(rows),{'covered_edges':len(used)}


def graph_sum_product(x,p):
    dictionary(x,('values','edges'));values=unique_ints(x['values'],1,p['maximum'],p['n'],p['n'],'values')
    es=edges(x['edges'],p['n']);require(len(es)==p['m'],'wrong edge count')
    sums={values[u]+values[v] for u,v in es};products={values[u]*values[v] for u,v in es}
    return max(len(sums),len(products)),{'distinct_sums':len(sums),'distinct_products':len(products)}


def no_equal_degree_path(x,p):
    n=p['n'];es=edges(x,n);a=adjacency(es,n);degrees=list(map(len,a))
    for u,v in es:
        # Both orientations of each middle edge are captured by its two sides.
        for s in a[u]-{v}:
            for t in a[v]-{u}:
                require(s==t or degrees[s]!=degrees[t],'length-three simple path has equal-degree endpoints')
    return len(es),{'degrees':degrees}


def sigma(n):
    result=1;d=2
    while d*d<=n:
        power=1;series=1
        while n%d==0:n//=d;power*=d;series+=power
        result*=series;d+=1
    if n>1:result*=n+1
    return result


def divisor_sum_ratio(x,p):
    a,b=sequence(x,2,2,'numerator and denominator')
    a=integer(a,1,p['maximum']);b=integer(b,1,p['maximum'])
    sa,sb=sigma(a),sigma(b);require(sa==sb,'divisor sums differ')
    error=abs(Fraction(a,b)-Fraction(*p['target']))
    return float(error),{'error_numerator':error.numerator,'error_denominator':error.denominator,'sigma':sa,'ratio':[a,b],'exact_feasibility':True,'score_serialization':'binary64 of exact rational error'}


def hypergraph_chromatic(x,p):
    dictionary(x,('edges','colors'));n=p['n'];k=p['colors'];rows=hyperedges(x['edges'],n,p['r'],1)
    colors=[integer(c,0,k-1,'color') for c in sequence(x['colors'],n,n,'colors')]
    require(all(len({colors[v] for v in edge})>1 for edge in rows),'provided coloring not proper')
    require(n<=12 and k<=3,'exhaustive lower-color search bounded')
    for c in product(range(k-1),repeat=n):
        require(any(len({c[v] for v in edge})==1 for edge in rows),'hypergraph admits fewer colors')
    return len(rows),{'chromatic_number':k,'uniformity':p['r']}


def square_extension(x,p):
    n=p['n']; values=unique_ints(x,n+1,n+p['maximum_window'],1,p['maximum_size'],'multipliers')
    value=n*prod(values);root=isqrt(value);require(root*root==value,'product is not square')
    return max(values)-n,{'multipliers':len(values),'square_root':str(root)}


def no_pairwise_sum_triple(x,p):
    values=unique_ints(x,1,p['n'],1,p['n'],'integers');a=set(values)
    for x,y,z in combinations(values,3):
        require(not(x+y in a and x+z in a and y+z in a),'three distinct elements and their pair sums occur')
    return len(values),{'three_generators_distinct':True}


def length_separated_sums(x,p):
    values=unique_ints(x,1,p['n'],1,p['maximum_size'],'integers')
    reachable=[1]+[0]*len(values)
    for index,a in enumerate(values):
        for k in range(index+1,0,-1):reachable[k]|=reachable[k-1]<<a
    seen=0
    for row in reachable:require(not row&seen,'equal sums use different numbers of terms');seen|=row
    return len(values),{'maximum_subset_sum':sum(values),'empty_sum_included':True}


def primitive_subset_sums(x,p):
    values=unique_ints(x,1,p['n'],1,p['maximum_size'],'integers');reachable=1
    for a in values:reachable|=reachable<<a
    total=sum(values)
    for s in range(1,total+1):
        if (reachable>>s)&1:
            require(all(not((reachable>>v)&1) for v in range(2*s,total+1,s)),'one nonempty subset sum divides another distinct value')
    return len(values),{'distinct_nonempty_subset_sums':reachable.bit_count()-1,'empty_sum_excluded':True}


def longest_path(x,p):
    n=p['n']; path=unique_ints(x,0,n-1,1,n,'path');es=edges(p['edges'],n)
    require(all(tuple(sorted(e)) in es for e in zip(path,path[1:])),'path uses nonedge')
    return len(path),{'path_edges':len(path)-1,'host_vertices':n}


def least_prime_factor(n):
    integer(n,2,10**7)
    for d in range(2,isqrt(n)+1):
        if n%d==0:return d
    return n


def rough_gap_witnesses(x,p):
    gaps=sequence(p['gaps'],1,100,'pinned gaps')
    answers=sequence(x,len(gaps),len(gaps),'gap witnesses');solved=[]
    for index,((lo,hi),m) in enumerate(zip(gaps,answers)):
        integer(lo,3,10**7);integer(hi,lo+1,10**7)
        require(least_prime_factor(lo)==lo and least_prime_factor(hi)==hi,
                'gap endpoints must be prime')
        require(all(least_prime_factor(v)!=v for v in range(lo+1,hi)),
                'gap endpoints are not consecutive primes')
        if m is None:continue
        m=integer(m,lo+1,hi-1,'interior witness')
        factor=least_prime_factor(m)
        require(factor>=hi-lo,'witness is not sufficiently rough')
        solved.append({'index':index,'least_prime_factor':factor})
    require(solved,'provide at least one valid gap witness')
    return len(solved),{'certified_gaps':solved,'total_gaps':len(gaps),
                        'unsolved_is_not_nonexistence_proof':True}


def distinct_multiple_span(x,p):
    values=unique_ints(x,1,p['maximum'],len(p['divisors']),len(p['divisors']),'representatives')
    require(all(v%d==0 for d,v in zip(p['divisors'],values)),
            'representative must be a multiple of its corresponding input')
    return max(values)-min(values),{'interval':[min(values),max(values)],
                                  'matched_divisors':len(values)}


def diameter_two_critical(x,p):
    n=p['n'];es=edges(x,n);a=adjacency(es,n)
    require(diameter(a)==2,'graph must have diameter exactly two')
    for u,v in es:
        a[u].remove(v);a[v].remove(u)
        d=diameter(a)
        require(d is None or d>2,'edge deletion leaves diameter at most two')
        a[u].add(v);a[v].add(u)
    return len(es),{'vertices':n,'edge_deletions_checked':len(es)}


def coprime_sum(x,p):
    values=unique_ints(x,1,p['n'],1,p['n'],'integers')
    require(all(gcd(a,b)==1 for a,b in combinations(values,2)),
            'members are not pairwise coprime')
    return sum(values),{'selected_integers':len(values)}


VERIFIERS={501:augment_diameter,506:homogeneous_partition,518:degree_diversity,
521:common_cycles,554:rough_gap_witnesses,572:no_singleton_intersection,
578:distinct_multiple_span,580:worst_matching_start,
585:clique_subdivision,592:mols,610:diameter_two_critical,614:hamilton_arrival,615:matching_arrival,
619:few_cycle_lengths,637:comparable_pairs,652:two_primitive,653:distinct_products,
655:acyclic_colors,664:biclique_partition,665:graph_sum_product,673:no_equal_degree_path,
679:divisor_sum_ratio,688:hypergraph_chromatic,697:square_extension,
717:no_pairwise_sum_triple,725:length_separated_sums,730:coprime_sum,
733:primitive_subset_sums,748:longest_path}


def evaluate(number,candidate,parameters):
    value,details=VERIFIERS[number](candidate,parameters)
    return value,{**details,'lean_verified':False,'finite_instance_only':True}
