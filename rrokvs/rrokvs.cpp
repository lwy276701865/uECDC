#include <cryptoTools/Network/IOService.h>
#include "SimpleIndex.h"
#include <iomanip>
#include <libOTe/Tools/LDPC/Util.h>
#include <libOTe_Tests/Common.h>
#include "Paxos.h"
#include "PaxosImpl.h"
#include <libdivide.h>
#include <stdint.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>  // 包含支持STL容器的头文件
using namespace oc;
using namespace volePSI;;
using namespace osuCrypto;
using namespace std;
namespace py = pybind11;
std::vector<uint32_t> encode(const std::vector<uint32_t>& py_key,const std::vector<uint32_t>& py_value,int n)
{
	int w=3;
	int ssp=40;
	int nt=0;
	int lbs=15;
	PaxosParam::DenseType dt = PaxosParam::DenseType::Binary;
	auto binSize = 1 << lbs;
	u64 baxosSize;
	Baxos paxos;
	paxos.init(n, binSize, w, ssp, dt, oc::ZeroBlock);
	baxosSize = paxos.size();
	std::vector<block> key, val, val2(n),pax(baxosSize);
    for (auto num : py_key) {  
        key.push_back(block(num));
    }
	for (auto num : py_value) {  
        val.push_back(block(num));
    }
	paxos.solve<block>(key, val, pax, nullptr, nt);
	std::vector<uint32_t>py_pax;
	for(block num:pax)
	{
		py_pax.push_back(num.get<u64>(0));
	}
	return py_pax;
}
std::vector<uint32_t> decode(const std::vector<uint32_t>& py_key,const std::vector<uint32_t>& py_pax,int n)
{
	int w=3;
	int ssp=40;
	int nt=0;
	int lbs=15;
	PaxosParam::DenseType dt = PaxosParam::DenseType::Binary;
	auto binSize = 1 << lbs;
	std::vector<block>pax;
	for(auto num:py_pax)
	{
		pax.push_back(block(num));
	}
	Baxos paxos;
	paxos.init(n, binSize, w, ssp, dt, oc::ZeroBlock);
	std::vector<block> key,val2(n);
    for (auto num : py_key) {  
        key.push_back(block(num));
    }
	paxos.decode<block>(key, val2, pax, nt);
	std::vector<uint32_t> py_val;
	for(block num:val2)
	{
		py_val.push_back(num.get<u64>(0));
	}
	return py_val;
}
PYBIND11_MODULE(rrokvs, m) {
    m.def("encode", &encode, "Call encode from static library");
    m.def("decode", &decode, "Call decode from static library");
}