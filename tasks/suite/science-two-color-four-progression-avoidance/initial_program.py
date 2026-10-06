"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
def construct():
    colors=[]
    for n in range(1,513):
        chosen=None
        for color in (0,1):
            if all(any(colors[n-1-j*d]!=color for j in (1,2,3)) for d in range(1,(n-1)//3+1)):
                chosen=color;break
        if chosen is None:break
        colors.append(chosen)
    return colors
# EVOLVE-BLOCK-END
