#include <KColorUtils>
#include <KImageCache>
#include <QColor>
#include <type_traits>

int main()
{
    static_assert(std::is_class_v<KImageCache>);
    KImageCache *cache = nullptr;
    (void)cache;
    const QColor black(Qt::black);
    const QColor white(Qt::white);
    return KColorUtils::contrastRatio(black, white) > 1.0 ? 0 : 1;
}
