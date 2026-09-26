#include <Prison/Barcode>
#include <Prison/VideoScanner>

int main()
{
    Prison::Barcode *barcode = nullptr;
    Prison::VideoScanner *scanner = nullptr;
    return (barcode || scanner) ? 1 : 0;
}
