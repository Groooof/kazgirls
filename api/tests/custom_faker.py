from faker import Faker
from faker.providers.file import Provider as MimeTypeProvider
from faker.providers.phone_number import Provider as PhoneNumberProvider

fake = Faker("ru_RU")
fake_en = Faker()


class MyPhoneProvider(PhoneNumberProvider):
    _mob_pattern_map = {
        "ru": "+79#########",
        "kz": "+77#########",
        "ua": "+380#########",
        "by": "+375#########",
    }

    def ru_phone_number(self, size: int = 1):
        return self._gen_phone_pattern(country_code="ru", is_mob=True, size=size)

    def ua_phone_number(self, size: int = 1):
        return self._gen_phone_pattern(country_code="ua", is_mob=True, size=size)

    def _gen_phone_pattern(self, country_code: str, is_mob: bool, size=1) -> str | list[str]:
        if is_mob:
            pattern = self._mob_pattern_map.get(country_code.lower())
        else:
            raise ValueError("City phones not found")

        if size > 1:
            return [self.numerify(self.generator.parse(pattern)) for _ in range(size)]
        return self.numerify(self.generator.parse(pattern))


fake.add_provider(MyPhoneProvider)


class CustomMimeTypeProvider(MimeTypeProvider):
    audio_mime_types = (
        "audio/mpeg",  # MP3 or other MPEG audio; Defined in RFC 3003
        "audio/wav",
        "audio/ogg",  # Ogg Vorbis, Speex, Flac and other audio; Defined in RFC 5334
    )

    def custom_mime_type(self, category: str | None = None) -> str:
        if category == "audio":
            return self.random_element(self.audio_mime_types)
        return super().mime_type(category)


fake.add_provider(CustomMimeTypeProvider)


def random_digits_str(digits: int | None = None, fix_len: bool = False) -> str:
    return str(fake.random_number(digits, fix_len))


def fake_set(n=10, build=fake.pyint, **kwargs):
    """Гарантировано n элементов"""
    res = set()

    while len(res) < n:
        res.add(build(**kwargs))

    return res
