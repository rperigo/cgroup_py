import cg_sockparse, sys

txt = cg_sockparse.parse_socketArgs(sys.argv[1:])

print txt
