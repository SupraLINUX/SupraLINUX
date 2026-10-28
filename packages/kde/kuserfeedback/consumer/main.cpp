#include <KUserFeedback/Provider>
#include <KUserFeedback/FeedbackConfigWidget>

int main()
{
    KUserFeedback::Provider *provider = nullptr;
    KUserFeedback::FeedbackConfigWidget *widget = nullptr;
    return (provider || widget) ? 1 : 0;
}
