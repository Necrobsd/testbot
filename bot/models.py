from django.core.signing import Signer
from django.db import models
from mptt.models import TreeForeignKey, MPTTModel


class Project(models.Model):
    """
    Класс модели проектов по заработку в интернете
    """
    title = models.CharField(max_length=254, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    image = models.ImageField(upload_to='projects_img',
                              verbose_name='Изображение',
                              blank=True)
    link = models.URLField(verbose_name='Ссылка на сайт',
                           blank=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = verbose_name_plural = 'Заработок в интернете'


class ReferralUser(MPTTModel):
    """
    Класс для модели пользователей телеграмм-бота
    """
    chat_id = models.IntegerField(unique=True,
                                  verbose_name='Идентификатор пользователя')
    name = models.CharField(max_length=100,
                            verbose_name='Имя пользователя')
    refer_code = models.CharField(max_length=30, db_index=True,
                                  verbose_name='Хэш для реферальной ссылки')
    parent = TreeForeignKey('self', on_delete=models.SET_NULL, db_index=True,
                            null=True, blank=True, related_name='child',
                            verbose_name='Пригласивший пользователь')
    balance = models.DecimalField(max_digits=50, decimal_places=2,
                                  verbose_name='Баланс', default=0)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # При сохранении пользователя добавляем ему реферальную ссылку
        if not self.refer_code:
            signer = Signer()
            self.refer_code = signer.signature(self.chat_id)
        super(ReferralUser, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class Order(models.Model):
    """
    Класс для модели Заказов.
    """
    name = models.CharField(max_length=100,
                            verbose_name='Имя заказчика')
    username = models.CharField(max_length=100,
                                verbose_name='Telegram Username')
    email = models.EmailField(verbose_name='E-mail адрес')
    phone = models.CharField(max_length=16,
                             verbose_name='Номер телефона')

# class OwnerContact(models.Model):
    """
    Класс для модели контактов собственника.
    Email и телеграмм контакты хозяина бота.

    """
    # email = models.EmailField(verbose_name='Е-mail адрес')
    # telegram = models.CharField(verbose_name='Идентификатор телеграмм аккаунта')