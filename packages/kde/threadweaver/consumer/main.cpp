#include <ThreadWeaver/Queue>
int main()
{
    ThreadWeaver::Queue queue;
    return queue.maximumNumberOfThreads() > 0 ? 0 : 1;
}
