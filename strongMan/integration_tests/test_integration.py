import os

from django.test import TestCase, Client
from django.contrib.auth.models import User

from strongMan.apps.connections.models import Connection, Child
from strongMan.apps.vici.wrapper.wrapper import ViciWrapper
from strongMan.apps.certificates.container_reader import X509Reader, PKCS1Reader
from strongMan.apps.certificates.services import UserCertificateManager
from strongMan.apps.certificates.models.certificates import Certificate


class IntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(username='testuser')
        self.user.set_password('12345')
        self.user.save()
        self.client.login(username='testuser', password='12345')
        ca_cert = Paths.strongSwan_cert.read()
        cert = Paths.carol_cert.read()
        key = Paths.carol_key.read()
        manager = UserCertificateManager()
        manager.add_keycontainer(cert)
        manager.add_keycontainer(key)
        manager.add_keycontainer(ca_cert)
        for c in Certificate.objects.all():
            if "carol@strongswan" in str(c.der_container):
                self.carol_cert = c
            else:
                self.ca_cert = c
        self.vici_wrapper = ViciWrapper()
        self.vici_wrapper.unload_all_connections()

    def test_Ike2EapIntegration(self):
        url_create = '/connections/add/'
        self.client.post(url_create, {'wizard_step': 'configure', 'gateway': '172.17.0.2', 'profile': 'EAP',
                                      'certificate': self.ca_cert.pk, 'identity': self.ca_cert.identities.first().pk,
                                      'username': "eap-test", 'password': "Ar3etTnp", 'form_name': 'Ike2EapForm'})

        self.assertEquals(1, Connection.objects.count())
        self.assertEquals(1, Child.objects.count())

        connection = Connection.objects.first().subclass()
        toggle_url = '/connections/toggle/'
        self.client.post(toggle_url, {'id': connection.id})

        self.assertEqual(self.vici_wrapper.get_connections_names().__len__(), 1)
        self.assertEqual(self.vici_wrapper.get_sas().__len__(), 1)
        self.client.post(toggle_url, {'id': connection.id})
        self.assertEqual(self.vici_wrapper.get_sas().__len__(), 0)

    def test_Ike2CertificateIntegration(self):
        url_create = '/connections/add/'
        self.client.post(url_create, {'wizard_step': 'configure', 'gateway': '172.17.0.2', 'profile': 'Cert',
                                      'certificate': self.carol_cert.pk, 'identity': self.carol_cert.identities.first().pk,
                                      'certificate_ca': self.ca_cert.pk, 'identity_ca': self.ca_cert.identities.first().pk,
                                      'form_name': 'Ike2CertificateForm'})
        self.assertEquals(1, Connection.objects.count())
        self.assertEquals(1, Child.objects.count())

        connection = Connection.objects.first().subclass()
        toggle_url = '/connections/toggle/'
        self.client.post(toggle_url, {'id': connection.id})

        self.assertEqual(self.vici_wrapper.get_connections_names().__len__(), 1)
        self.assertEqual(self.vici_wrapper.get_sas().__len__(), 1)
        self.client.post(toggle_url, {'id': connection.id})
        self.assertEqual(self.vici_wrapper.get_sas().__len__(), 0)

    def test_Ike2EapCertificateIntegration(self):
        url_create = '/connections/add/'
        self.client.post(url_create, {'wizard_step': 'configure', 'gateway': '172.17.0.2', 'profile': 'Eap+Cert',
                                      'username': "eap-test", 'password': "Ar3etTnp",
                                      'certificate': self.carol_cert.pk, 'identity': self.carol_cert.identities.first().pk,
                                      'certificate_ca': self.ca_cert.pk, 'identity_ca': self.ca_cert.identities.first().pk,
                                      'form_name': 'Ike2EapCertificateForm'})
        self.assertEquals(1, Connection.objects.count())
        self.assertEquals(1, Child.objects.count())

        connection = Connection.objects.first().subclass()
        toggle_url = '/connections/toggle/'
        self.client.post(toggle_url, {'id': connection.id})

        self.assertEqual(self.vici_wrapper.get_connections_names().__len__(), 1)
        self.assertEqual(self.vici_wrapper.get_sas().__len__(), 1)
        self.client.post(toggle_url, {'id': connection.id})
        self.assertEqual(self.vici_wrapper.get_sas().__len__(), 0)


class TestCert:
    def __init__(self, path):
        self.path = path
        self.dir = os.path.dirname(os.path.realpath(__file__))

    def read(self):
        absolute_path = self.dir + "/certs/" + self.path
        with open(absolute_path, 'rb') as f:
            return f.read()

    def read_x509(self, password=None):
        bytes = self.read()
        reader = X509Reader.by_bytes(bytes, password)
        reader.parse()
        return reader

    def read_pkcs1(self, password=None):
        bytes = self.read()
        reader = PKCS1Reader.by_bytes(bytes, password)
        reader.parse()
        return reader


class Paths:
    carol_cert = TestCert("carolCert.pem")
    carol_key = TestCert("carolKey.pem")
    strongSwan_cert = TestCert("strongswanCert.pem")