import traceback
try:
    import app.main
except Exception as e:
    with open("error_trace.txt", "w") as f:
        traceback.print_exc(file=f)
