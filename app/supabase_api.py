"""User-JWT-only REST client; never use admin/service keys."""
import json
import urllib.error
import urllib.parse
import urllib.request

class Api:
    def __init__(self,url,key):
        if not url.startswith('https://') or not key or key.startswith('sb_secret_'):
            raise ValueError('Use HTTPS Project URL and Publishable/anon key, never secret/service_role')
        self.url=url.rstrip('/'); self.key=key;self.token=None; self.user_id=None

    def _req(self,path,method='GET',payload=None,params=None,headers=None):
        uri=self.url+path
        if params:uri+='?'+urllib.parse.urlencode(params)
        hdr={'apikey':self.key,'Authorization':'Bearer '+(self.token or self.key)}
        data=None
        if payload is not None:
            data=json.dumps(payload,ensure_ascii=False).encode('utf8');hdr['Content-Type']='application/json'
        hdr.update(headers or {})
        try:
            with urllib.request.urlopen(urllib.request.Request(uri,headers=hdr,data=data,method=method),timeout=25) as r:
                raw=r.read();return json.loads(raw) if raw else None
        except urllib.error.HTTPError as err:
            body=err.read().decode('utf8','replace')[:350]
            raise RuntimeError(f'HTTP {err.code}: {body}') from err
        except urllib.error.URLError as err:
            raise RuntimeError('Network unavailable: '+str(err.reason)) from err

    def login(self,email,password):
        auth=self._req('/auth/v1/token?grant_type=password','POST',{'email':email,'password':password})
        self.token=auth['access_token'];self.user_id=auth['user']['id']
        return self.user_id

    def list(self,table,params):
        return self._req('/rest/v1/'+table,params=params) or []

    def create(self,table,payload):
        return self._req('/rest/v1/'+table,'POST',payload,headers={'Prefer':'return=minimal'})

    def update(self,table,identifier,patch,extra_filters=None):
        params={'id':'eq.'+str(identifier)}
        params.update(extra_filters or {})
        return self._req('/rest/v1/'+table,'PATCH',patch,params,headers={'Prefer':'return=representation'}) or []

    def delete(self,table,identifier):
        return self._req('/rest/v1/'+table,'DELETE',params={'id':'eq.'+identifier})
