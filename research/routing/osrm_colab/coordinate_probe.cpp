// Check the original header as-is; do not hide missing includes with a prelude.
#include "util/coordinate.hpp"

int main()
{
    osrm::util::Coordinate coordinate{osrm::util::FixedLongitude{90400000},
                                      osrm::util::FixedLatitude{23800000}};
    auto longitude = osrm::util::toFixed(osrm::util::FloatLongitude{90.4});
    return coordinate.lon == longitude &&
                   coordinate.lat == osrm::util::FixedLatitude{23800000}
               ? 0
               : 1;
}
