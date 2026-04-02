FC      = gfortran
FFLAGS  = -Wall -Wextra -std=f2008
TARGET  = bmssp

.PHONY: all release debug test clean

all: release

release: FFLAGS += -O2
release: $(TARGET)

debug: FFLAGS += -g -fcheck=all -fbacktrace
debug: $(TARGET)

$(TARGET): bmssp.f90
	$(FC) $(FFLAGS) $< -o $@

test: release
	python -m pytest tests/ -v

clean:
	rm -f $(TARGET) *.o *.mod
