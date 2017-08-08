FROM archlinux/base
MAINTAINER Barry Moore "moore0557@gmail.com"
RUN pacman -Syyu --noconfirm
RUN pacman -S python python-pip --noconfirm
COPY app.py requirements.txt /app/
WORKDIR /app
RUN pip install -r requirements.txt
RUN rm -rf /var/cache/pacman/pkg
RUN rm -rf ~/.cache/pip
CMD ["gunicorn", "-w", "1", "-b", ":8000", "app:server"]
