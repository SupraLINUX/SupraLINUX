#include <KCodecs>
#include <QByteArray>
int main()
{
    const QByteArray encoded = KCodecs::base64Encode(QByteArray("SupraLINUX"));
    return encoded.isEmpty() ? 1 : 0;
}
