"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    answers=[]
    for n in range(3,257):
        found=None
        # Search only the first possible smallest denominator; deliberately limited baseline.
        x=n//4+1
        a=4*x-n;b=n*x
        for y in range(max(x+1,b//a+1),2*b//a+1):
            denominator=a*y-b
            if b*y%denominator==0:
                z=b*y//denominator
                if z>y:
                    found=[x,y,z];break
        answers.append(found)
    return answers
# EVOLVE-BLOCK-END
