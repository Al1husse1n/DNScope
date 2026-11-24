import asyncio
import secrets

from dnscope.auth.passwords import compute_hmac, compute_hmac_prefix, hash_api_key
from dnscope.config import Settings
from dnscope.db.repository import ApiKeyRepository
from dnscope.db.session import build_engine, build_session_factory


async def seed_admin_key(name: str = "default-admin") -> str:
    settings = Settings()
    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)

    raw_key = secrets.token_urlsafe(32)
    secret = settings.api_key_hmac_secret
    hmac_key = compute_hmac(raw_key, secret)
    hmac_prefix = compute_hmac_prefix(raw_key, secret)
    stored_hash = hash_api_key(hmac_key)

    async with session_factory() as session:
        repo = ApiKeyRepository(session)
        await repo.create(
            name=name,
            key_hash=stored_hash,
            hmac_prefix=hmac_prefix,
            role="admin",
        )
        await session.commit()

    await engine.dispose()
    return raw_key


def main() -> None:
    raw_key = asyncio.run(seed_admin_key())
    print("\n===========================================================")
    print("ADMIN API KEY GENERATED:")
    print(raw_key)
    print("WARNING: STORE THIS SECURELY - IT WILL NOT BE SHOWN AGAIN")
    print("===========================================================\n")


if __name__ == "__main__":
    main()
