// SPDX-FileCopyrightText: 2026 SupraLINUX contributors
// SPDX-License-Identifier: CC0-1.0
#include <PipeWireSourceStream>
#include <PipeWireRecord>
#include <DmaBufHandler>
#include <QGuiApplication>
#include <QCoreApplication>
#include <QElapsedTimer>
#include <QThread>
#include <QFileInfo>
#include <QQmlEngine>
#include <QQmlComponent>
#include <memory>
#include <iostream>
#include <functional>
static bool until(const std::function<bool()> &predicate, int milliseconds=10000) {
 QElapsedTimer timer;timer.start();
 while (!predicate() && timer.elapsed()<milliseconds) {QCoreApplication::processEvents(QEventLoop::AllEvents,20);QThread::msleep(5);}
 return predicate();
}
static int fail(const char *message) {std::cerr<<message<<'\n';return 1;}
int main(int argc,char **argv) {
 QGuiApplication app(argc,argv);
 if(argc!=3)return fail("Expected private node ID and output path");
 bool idOk=false;const uint node=QString::fromLocal8Bit(argv[1]).toUInt(&idOk);
 if(!idOk || !node)return fail("Invalid private source node");
 PipeWireSourceStream stream;
 stream.setAllowDmaBuf(false);stream.setUsageHint(PipeWireSourceStream::UsageHint::EncodeSoftware);stream.setMaxFramerate({30,1});
 int frames=0;QString frameError;QImage copiedImage;std::shared_ptr<PipeWireFrameData> copy;
 QObject::connect(&stream,&PipeWireSourceStream::frameReceived,&app,[&](const PipeWireFrame &frame){
  if(frame.dmabuf || !frame.dataFrame){frameError=QStringLiteral("Expected CPU image from isolated video source");return;}
  const auto image=frame.dataFrame->toImage();
  if(image.isNull() || image.size()!=QSize(160,120) || image.size()!=stream.size()){frameError=QStringLiteral("Actual frame pixels or dimensions invalid");return;}
  bool varied=false;const auto first=image.pixel(0,0);
  for(int x=0;x<image.width();x++)if(image.pixel(x,image.height()/2)!=first)varied=true;
  if(image.pixelColor(12,15).red()!=36 || image.pixelColor(12,15).green()!=75){std::cerr<<"Frame format="<<frame.format<<" QImage="<<image.format()<<" pixel="<<image.pixelColor(12,15).red()<<","<<image.pixelColor(12,15).green()<<","<<image.pixelColor(12,15).blue()<<" stride="<<frame.dataFrame->stride<<"\n";frameError=QStringLiteral("Actual pixel channels do not match the private RGBA pattern");return;}
  if(!varied){frameError=QStringLiteral("Test pattern is unexpectedly uniform");return;}
  if(!copy){copy=frame.dataFrame->copy();if(!copy || copy->data==frame.dataFrame->data){frameError=QStringLiteral("Frame copy must own different pixel storage");return;}copiedImage=image.copy();}
  ++frames;
 });
 if(!stream.createStream(node,0))return fail("Unable to connect public source stream");
 if(!until([&](){return frames>=10 || !frameError.isEmpty();}) || !frameError.isEmpty()){std::cerr<<stream.error().toStdString()<<' '<<frameError.toStdString()<<'\n';return fail("Actual synthetic-frame delivery failed");}
 stream.setActive(false);
 if(!copy || copy->toImage()!=copiedImage)return fail("Independent frame data did not survive source-buffer recycling");
 DmaBufHandler handler;
 QQmlEngine engine;
 for(const QByteArray &qml: {QByteArray("import QtQuick\nimport org.kde.pipewire 1.0\nPipeWireSourceItem { allowDmaBuf: false }"),QByteArray("import org.kde.pipewire.record 1.0\nPipeWireRecord {}")}) {
  QQmlComponent component(&engine);component.setData(qml,QUrl());
  std::unique_ptr<QObject> object(component.create());
  if(!object){std::cerr<<component.errorString().toStdString();return fail("Installed QML consumer unavailable");}
 }
 QQmlComponent monitorComponent(&engine);
 monitorComponent.setData("import org.kde.pipewire.monitor 1.0 as Monitor\nMonitor.MediaMonitor { role: Monitor.MediaRole.Camera; property int fixtureCameraRole: Monitor.MediaRole.Camera; property int fixtureMusicRole: Monitor.MediaRole.Music; property int legacyMusicRole: Monitor.MediaMonitor.Music; property int legacyCameraRole: Monitor.MediaMonitor.Camera; property bool legacyRoleIsUndefined: typeof Monitor.MediaMonitor.Music === \"undefined\" }",QUrl());
 std::unique_ptr<QObject> monitor(monitorComponent.create());
 if(!monitor){std::cerr<<monitorComponent.errorString().toStdString();return fail("Installed MediaMonitor QML unavailable");}
 if(monitor->property("legacyMusicRole")!=monitor->property("fixtureMusicRole") || monitor->property("legacyCameraRole")!=monitor->property("fixtureCameraRole"))return fail("Legacy MediaMonitor role enums differ from MediaRole");
 if(!until([&](){return monitor->property("detectionAvailable").toBool() && monitor->property("count").toInt()==1;}))return fail("Actual private camera source is absent from MediaMonitor");
 if(!monitor->setProperty("role",monitor->property("fixtureMusicRole")) || !until([&](){return monitor->property("detectionAvailable").toBool() && monitor->property("count").toInt()==0;}))return fail("MediaMonitor role filtering failed");
 if(!monitor->setProperty("role",monitor->property("fixtureCameraRole")) || !until([&](){return monitor->property("detectionAvailable").toBool() && monitor->property("count").toInt()==1;}))return fail("MediaMonitor reconnection failed");
 std::cout<<"MediaMonitor private source detection, role filtering and reconnection: PASS; legacy MediaMonitor.Music undefined="<<monitor->property("legacyRoleIsUndefined").toBool()<<'\n';
 PipeWireRecord record;
 record.setNodeId(node);record.setEncoder(PipeWireBaseEncodedStream::VP8);record.setMaxFramerate(30);record.setMaxPendingFrames(6);record.setOutput(QString::fromLocal8Bit(argv[2]));
 if(record.nodeId()!=node || record.encoder()!=PipeWireBaseEncodedStream::VP8 || record.state()!=PipeWireBaseEncodedStream::Idle)return fail("Public recording properties invalid");
 QString recordingError;QObject::connect(&record,&PipeWireBaseEncodedStream::errorFound,&app,[&](const QString &error){recordingError=error;});
 record.start();
 if(!until([&](){return record.state()==PipeWireBaseEncodedStream::Recording || !recordingError.isEmpty();}) || !recordingError.isEmpty()){std::cerr<<recordingError.toStdString()<<'\n';return fail("Actual software recording did not start");}
 QElapsedTimer recording;recording.start();until([&](){return recording.elapsed()>=1200 || !recordingError.isEmpty();},2000);
 record.stop();
 if(!until([&](){return record.state()==PipeWireBaseEncodedStream::Idle;}) || !recordingError.isEmpty() || QFileInfo(record.output()).size()<=0)return fail("Actual recording did not flush to a nonempty file");
 std::cout<<"Actual CPU source frames, independent frame copy, installed QML modules and VP8 recording: PASS; frames="<<frames<<" size="<<copiedImage.width()<<'x'<<copiedImage.height()<<'\n';
 return 0;
}
