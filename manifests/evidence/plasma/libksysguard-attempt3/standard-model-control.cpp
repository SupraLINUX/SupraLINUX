#include <QCoreApplication>
#include <QStandardItemModel>
#include <QAbstractItemModelTester>
int main(int argc,char **argv) {
 QCoreApplication app(argc,argv);
 QStandardItemModel model;
 QAbstractItemModelTester tester(&model,QAbstractItemModelTester::FailureReportingMode::Fatal);
 model.appendRow(new QStandardItem(QStringLiteral("first")));
 model.clear();
 model.appendRow(new QStandardItem(QStringLiteral("second")));
 return model.rowCount()==1 ? 0 : 1;
}
