"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
from itertools import combinations

def construct():
    smooth=[]
    for x in range(1,129):
        y=x
        for p in (2,3,5):
            while y%p==0:y//=p
        if y==1:smooth.append(x)
    answers=[]
    for n in range(1,129):
        answer=None
        for count in (3,2,1):
            for terms in combinations([x for x in smooth if x<=n],count):
                if sum(terms)==n and all(b%a for a,b in combinations(terms,2)):
                    answer=list(terms);break
            if answer is not None:break
        answers.append(answer)
    return answers
# EVOLVE-BLOCK-END
