#include <KHolidays/LunarPhase>
#include <QDate>

int main()
{
    const auto phase = KHolidays::LunarPhase::phaseAtDate(QDate(2026, 1, 1));
    (void)phase;
    return 0;
}
