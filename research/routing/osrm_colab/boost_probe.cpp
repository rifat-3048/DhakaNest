// Link against the installed Boost libraries without changing OSRM source.
#include <boost/version.hpp>
#include <boost/filesystem.hpp>
#include <boost/program_options.hpp>

static_assert(BOOST_VERSION == EXPECTED_BOOST, "Unexpected Boost headers");

int main()
{
    boost::program_options::options_description options("probe");
    options.add_options()("probe", "probe");
    return boost::filesystem::exists(boost::filesystem::path(".")) ? 0 : 1;
}
