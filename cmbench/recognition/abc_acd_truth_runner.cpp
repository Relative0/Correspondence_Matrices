// Thin executable adapter around the pinned public ABC ACD header implementation.
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <intrin.h>
#include <stdexcept>
#include <string>
#include <vector>

// ABC revision baf4ddb uses this GNU intrinsic spelling in its ACD headers.
#define __builtin_popcountl __popcnt

#include "misc/util/abc_global.h"
#include "map/if/acd/ac_decomposition.hpp"

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "usage: acd_truth_runner <n_vars> <lut_size> <truth_bits_hex>\n";
        return 64;
    }
    try {
        const unsigned n_vars = static_cast<unsigned>(std::stoul(argv[1]));
        const int lut_size = std::stoi(argv[2]);
        if (n_vars < 2 || n_vars > 8 || lut_size < 2 || lut_size > 8) {
            throw std::invalid_argument("bounded ACD inputs required");
        }
        std::string text = argv[3];
        if (text.rfind("0x", 0) == 0 || text.rfind("0X", 0) == 0) {
            text.erase(0, 2);
        }
        const unsigned truth_bits = 1U << n_vars;
        if (text.empty() || text.size() > (truth_bits + 3) / 4) {
            throw std::invalid_argument("truth vector exceeds n_vars bound");
        }
        std::vector<word> truth((truth_bits + 63) / 64, 0);
        for (std::size_t offset = 0; offset < text.size(); ++offset) {
            const char character = text[text.size() - 1 - offset];
            const unsigned value = character >= '0' && character <= '9' ? character - '0'
                : character >= 'a' && character <= 'f' ? character - 'a' + 10
                : character >= 'A' && character <= 'F' ? character - 'A' + 10 : 16;
            if (value >= 16) {
                throw std::invalid_argument("truth vector is not hexadecimal");
            }
            truth[offset / 16] |= word(value) << ((offset % 16) * 4);
        }
        unsigned delay = 0;
        unsigned cost = 0;
        using namespace acd;
        ac_decomposition_params parameters;
        parameters.lut_size = lut_size;
        parameters.use_first = false;
        parameters.try_no_late_arrival = true;
        ac_decomposition_stats statistics;
        const auto started = std::chrono::steady_clock::now();
        ac_decomposition_impl decomposition(n_vars, parameters, &statistics);
        const int result = decomposition.run(truth.data(), delay);
        const auto algorithm_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now() - started).count();
        if (result < 0) {
            delay = 0;
        } else {
            delay = decomposition.get_profile();
            cost = statistics.num_luts;
        }
        std::cout << "{\"n_vars\":" << n_vars
                  << ",\"lut_size\":" << lut_size
                  << ",\"status\":\"" << (result < 0 ? "no_decomposition" : "decomposed") << "\""
                  << ",\"return_value\":" << result
                  << ",\"delay_profile\":" << delay
                  << ",\"lut_cost\":" << cost
                  << ",\"algorithm_ns\":" << algorithm_ns << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 65;
    }
}
