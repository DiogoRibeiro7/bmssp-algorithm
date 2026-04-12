CXX     = g++
CXXFLAGS = -Wall -Wextra -std=c++17
TARGET  = bmssp

.PHONY: all release debug test clean

all: release

release: CXXFLAGS += -O2
release: $(TARGET)

debug: CXXFLAGS += -g -O0
debug: $(TARGET)

$(TARGET): bmssp.cpp
	$(CXX) $(CXXFLAGS) $< -o $@

test: release
	python -m pytest tests/ -v

clean:
	rm -f $(TARGET) $(TARGET).exe
