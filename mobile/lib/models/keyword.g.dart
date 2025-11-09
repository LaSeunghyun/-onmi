// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'keyword.dart';

// **************************************************************************
// TypeAdapterGenerator
// **************************************************************************

class KeywordAdapter extends TypeAdapter<Keyword> {
  @override
  final int typeId = 0;

  @override
  Keyword read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return Keyword(
      id: fields[0] as String,
      text: fields[1] as String,
      status: fields[2] as String,
      notifyLevel: fields[3] as String,
      autoShareEnabled: fields[4] as bool,
      autoShareChannels: (fields[5] as List).cast<String>(),
      createdAt: fields[6] as DateTime,
      lastCrawledAt: fields[7] as DateTime?,
    );
  }

  @override
  void write(BinaryWriter writer, Keyword obj) {
    writer
      ..writeByte(8)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.text)
      ..writeByte(2)
      ..write(obj.status)
      ..writeByte(3)
      ..write(obj.notifyLevel)
      ..writeByte(4)
      ..write(obj.autoShareEnabled)
      ..writeByte(5)
      ..write(obj.autoShareChannels)
      ..writeByte(6)
      ..write(obj.createdAt)
      ..writeByte(7)
      ..write(obj.lastCrawledAt);
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is KeywordAdapter &&
          runtimeType == other.runtimeType &&
          typeId == other.typeId;
}
