# Third-party notices / 素材について

Every file in this repository is covered by the MIT license in
[LICENSE](LICENSE). There are no third-party assets with separate terms.
This file just records where the bundled images came from.

本リポジトリのファイルはすべて [LICENSE](LICENSE) のMITライセンスで配布しています。
別条件の第三者素材は含まれていません。以下は同梱画像の出自の記録です。

---

## assets/*.png — character parts

The 17 character part images were generated with **Higgsfield GPT Image 2.5**:
one base illustration was split into layers, with the hidden areas behind each
part filled in so the rig does not show holes when it moves.

キャラクターのパーツ画像17枚は **Higgsfield GPT Image 2.5** で生成しました。
1枚のベース画像をレイヤーごとに分解し、隠れていた部分を補完しているので、
パーツが動いても穴が出ません。

## assets/rooftop.jpg, beach.jpg, park.jpg — backgrounds

The three background plates were generated with **ChatGPT (GPT-6 Astra)** and
re-encoded to JPEG for this repository. They contain no identifiable people,
logos or readable signage.

背景3枚は **ChatGPT（GPT-6 Astra）** で生成し、リポジトリ用にJPEGへ再エンコード
したものです。実在の人物・ロゴ・読める看板は写っていません。

---

## Runtime dependencies

The app ships no third-party code. It uses only the Python standard library and
calls **FFmpeg** as an external executable — FFmpeg is not bundled and must be
installed separately. See https://ffmpeg.org/legal.html for its licensing.

`tools/prepare_assets.py` is the only script needing a third-party package
(Pillow). It is a build-time helper and is not used by the app at runtime.

アプリ本体に同梱している第三者コードはありません。Python標準ライブラリのみを使い、
FFmpegは外部コマンドとして呼び出します（同梱はしていません）。
`tools/prepare_assets.py` だけが Pillow を必要としますが、これは素材を作り直すときの
補助スクリプトで、アプリの実行には使いません。
