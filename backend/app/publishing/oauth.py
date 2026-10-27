import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from app.db import utcnow
from app.models import Channel, OAuthToken

SCOPE = "https://www.googleapis.com/auth/youtube.upload"


# no real Google OAuth in the prototype
def link_channel(db: Session, channel: Channel):
    db.query(OAuthToken).filter(OAuthToken.channel_id == channel.id).delete()
    channel.youtube_channel_id = "UC" + secrets.token_urlsafe(16)[:22]
    db.add(OAuthToken(channel_id=channel.id, access_token_enc="enc:" + secrets.token_urlsafe(24),
                      refresh_token_enc="enc:" + secrets.token_urlsafe(24), scope=SCOPE,
                      expires_at=utcnow() + timedelta(hours=1)))
