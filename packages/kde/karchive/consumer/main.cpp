#include <KArchive/KZip>
#include <QString>

int main()
{
    KZip archive(QStringLiteral("/tmp/supralinux-karchive-consumer.zip"));
    archive.setCompression(KZip::NoCompression);
    return archive.compression() == KZip::NoCompression ? 0 : 1;
}
