Blender-XFileImporter
=====================

Import DirectX-X-MeshFile to Blender

## 概要
3DCGソフトであるBlenderにDirectXのXファイルをインポートするPythonスクリプトです。
アドオンではありません。

## 使い方
3つのファイル、XFileImmporter、XFileHelper、XFileParserをBlenderで開きます。
XFileImporterのfilepath変数に読み込むXファイルのパスを指定して、
スクリプトを実行してください。

## 対応状況
- 日本語に対応してません。
テクスチャファイル名はすべてASCIIで表現できる文字のみにしてください。
- アニメーション、ボーン、フレームなどには対応しません。
- テキスト形式に対応しますが、バイナリ形式に対応できません。
DirectX SDK Toolsのメッシュコンバーターでテキスト形式に変換するか、
PMXEditorでエクスポートしてください。

## 開発お願い
本当はいろいろ対応させたり、アドオンにしたかったですが、
私の技術不足でできませんでした。
出来る人は開発をお願いします。

XFileHelperおよびXFileParseはAssimpのC++言語のソースコードをPythonに対応させる形にしています。
大量の文字の構文解析には時間がかかるので、正規表現で文字列分割させてます。
一度メモリに展開し、さらに数値に変換するのでメモリを多く食います