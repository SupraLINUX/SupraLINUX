KDarkLightTransition::Relation KDarkLightTransition::test(const QDateTime &dateTime) const
{
    const int tolerance = 60;
    if (dateTime.secsTo(m_startDateTime) > tolerance) {
        return Relation::Upcoming;
    } else if (dateTime.secsTo(m_endDateTime) > tolerance) {
        return Relation::InProgress;
    } else {
        return Relation::Passed;
    }
}
