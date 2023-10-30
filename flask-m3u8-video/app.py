from datetime import datetime
import hashlib
import os
import pathlib
from flask import Flask, render_template, request
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa

# 创建应用程序 app
app = Flask(__name__)
# 配置 SQLite 数据库, 默认存放在 app instance 文件夹下
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"
# 图片默认的上传地址
app.config["UPLOAD_FOLDER"] = "static/upload/video"

# 创建拓展插件实例
db = SQLAlchemy()
# 将拓展插件对象绑定到程序实例
db.init_app(app)


class MovieORM(db.Model):
    __tablename__ = "movie"
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(255), nullable=False)
    url = sa.Column(sa.String(255), nullable=False)
    m3u8_url = sa.Column(sa.String(255), nullable=True)
    create_at = sa.Column(sa.DateTime, default=datetime.now)


@app.cli.command()
def create():
    db.drop_all()
    db.create_all()


@app.get("/upload_movie")
def upload_movie():
    return render_template("video_upload.html")


@app.post("/video_upload")
def upload_movie2():
    file = request.files["file"]
    if file:
        """接收并保存视频文件"""
        filename = file.filename
        # 读取视频内容
        content = file.read()
        # 获取视频的 md5 值
        hex_name = hashlib.md5(content).hexdigest()
        # 获取文件后缀
        suffix = pathlib.Path(filename).suffix
        # 拼接新的名字 hex + 原有后缀
        new_filename = hex_name + suffix
        print("new_filename", new_filename)

        upload_dir = pathlib.Path(app.config["UPLOAD_FOLDER"])
        # 获取写入地址
        new_path = upload_dir.joinpath(new_filename)
        # 写入文件
        open(new_path, mode="wb").write(content)

        """处理为 m3u8 视频格式"""
        # 构建 m3u8 视频存放目录
        m3u8_path = upload_dir.parent.joinpath("m3u8")
        if not m3u8_path.exists():
            m3u8_path.mkdir()

        current_dir = m3u8_path.joinpath(hex_name)
        if not current_dir.exists():
            # m3u8 处理
            current_dir.mkdir()

        # 指令1 生成 ts 文件
        cli1 = f"ffmpeg -y -i {new_path} -vcodec copy -acodec copy -bsf:v h264_mp4toannexb {str(current_dir)}/index.ts"
        os.system(cli1)
        print("cli1:", cli1)
        # 指令2 分割 ts 片段， 生成 m3u8 索引文件
        cli2 = f'ffmpeg -i {str(current_dir)}/index.ts -c copy -map 0 -f segment -segment_list {str(current_dir)}/index.m3u8 -segment_time 10 "{str(current_dir)}/index-%04d.ts"'
        os.system(cli2)
        print("cli2", cli2)

        # 创建模型并保存到数据库
        mv = MovieORM()
        mv.url = "/" + str(new_path)
        mv.name = filename
        mv.m3u8_url = "/" + str(current_dir) + "/index.m3u8"
        db.session.add(mv)
        db.session.commit()

    return {"code": 0, "msg": "上传视频成功"}


@app.route("/", methods=["GET"])
def hello_world():
    q = db.select(MovieORM)
    movie_list = db.session.execute(q).scalars()
    return render_template("index.html", movie_list=movie_list)


@app.route("/video_view")
def video_view():
    vid = request.args.get("video_id")
    video = MovieORM.query.get(vid)
    return render_template("video_view.html", url=video.m3u8_url.replace('\\', '/'))


if __name__ == "__main__":
    app.run(debug=True)
