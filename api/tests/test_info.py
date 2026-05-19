from unittest.mock import patch

from rest_framework.test import (
    APITestCase,
    APIClient
)

from django.urls import (
    reverse
)

from api.models import (
    Plant
)

from api.views.views_info import (
    getTemperature,
    resolveScientificName
)


class TestPlantInfoAPI(
    APITestCase
):

    def setUp(
        self
    ):

        self.client=(
            APIClient()
        )

        self.URL=(
            reverse(
                "importPlant"
            )
        )

    ################################
    # helpers
    ################################

    def test_get_temperature(
        self
    ):

        low,high=(
            getTemperature(
                1,
                3
            )
        )

        self.assertEqual(
            low,
            -51.1
        )

        self.assertEqual(
            high,
            24
        )


    def test_get_temperature_none(
        self
    ):

        result=(
            getTemperature(
                None,
                None
            )
        )

        self.assertEqual(
            result,
            (
                None,
                None
            )
        )


    @patch(
        "api.views.views_info.requests.get"
    )
    def test_resolve_synonym(
        self,
        mock_get
    ):

        mock_get.return_value.json.return_value={
            "synonym":True,
            "species":
            "Rosa canina"
        }

        mock_get.return_value.raise_for_status=(
            lambda:None
        )

        result=(
            resolveScientificName(
                "rose"
            )
        )

        self.assertEqual(
            result,
            "Rosa canina"
        )


    @patch(
        "api.views.views_info.requests.get"
    )
    def test_resolve_exception(
        self,
        mock_get
    ):

        mock_get.side_effect=(
            Exception()
        )

        result=(
            resolveScientificName(
                "rose"
            )
        )

        self.assertEqual(
            result,
            "rose"
        )

    ################################
    # endpoint
    ################################

    def test_missing_name(
        self
    ):

        response=(
            self.client.get(
                self.URL
            )
        )

        self.assertEqual(
            response.status_code,
            400
        )


    @patch(
        "api.views.views_info.getInfoPlant"
    )
    def test_get_success(
        self,
        mock_info
    ):

        mock_info.return_value={

            "scientificName":
            "Rose"

        }

        response=(
            self.client.get(
                self.URL,
                {
                    "scientificName":
                    "Rose",

                    "lang":
                    "en"
                }
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )


    @patch(
        "api.views.views_info.getInfoPlant"
    )
    def test_post_success(
        self,
        mock_info
    ):

        mock_info.return_value={

            "scientificName":
            "Rose"

        }

        response=(
            self.client.post(
                self.URL,
                {
                    "scientificName":
                    "Rose",

                    "lang":
                    "en"
                }
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )


    @patch(
        "api.views.views_info.getInfoPlant"
    )
    def test_not_found(
        self,
        mock_info
    ):

        mock_info.return_value=None

        response=(
            self.client.get(
                self.URL,
                {
                    "scientificName":
                    "fake"
                }
            )
        )

        self.assertEqual(
            response.status_code,
            404
        )


    @patch(
        "api.views.views_info.getInfoPlant"
    )
    def test_exception(
        self,
        mock_info
    ):

        mock_info.side_effect=(
            Exception(
                "boom"
            )
        )

        response=(
            self.client.get(
                self.URL,
                {
                    "scientificName":
                    "Rose"
                }
            )
        )

        self.assertEqual(
            response.status_code,
            500
        )


    ################################
    # existing plant path
    ################################

    @patch(
        "api.views.views_info.translate_text"
    )
    def test_existing_plant(
        self,
        mock_translate
    ):

        Plant.objects.create(

            scientificName=
            "Rose",

            commonName=
            "Rose",

            family=
            "Rosaceae",

            canFlower=
            True,

            minTemperature=
            5,

            maxTemperature=
            30,

            description=
            "desc"
        )

        mock_translate.side_effect=[

            "descripcion",

            "rosa"

        ]

        response=(
            self.client.get(
                self.URL,
                {
                    "scientificName":
                    "Rose",

                    "lang":
                    "es"
                }
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )


    ################################
    # create new path
    ################################

    @patch(
        "api.views.views_info.createPlantImages"
    )
    @patch(
        "api.views.views_info.getPlantInfoFromAPI"
    )
    def test_create_new(
        self,
        mock_api,
        mock_images
    ):

        mock_api.return_value={

            "common_name":
            "rose",

            "family":
            "Rosaceae",

            "flowers":
            True,

            "description":
            "desc",

            "hardiness":{

                "min":1,

                "max":2
            }
        }

        response=(
            self.client.get(
                self.URL,
                {
                    "scientificName":
                    "Rosa canina",

                    "lang":
                    "en"
                }
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTrue(

            Plant.objects.filter(
                scientificName=
                "Rosa canina"
            ).exists()

        )

    ################################
    # inferCanFlowerFromGBIF
    ################################

    @patch(
        "api.views.views_info.requests.get"
    )
    def test_gbif_class_true(
            self,
            mock_get
    ):
        mock_get.return_value.json.return_value = {

            "class":
                "magnoliopsida"
        }

        from api.views.views_info import (
            inferCanFlowerFromGBIF
        )

        self.assertTrue(

            inferCanFlowerFromGBIF(
                "rose"
            )

        )

    @patch(
        "api.views.views_info.requests.get"
    )
    def test_gbif_phylum_false(
            self,
            mock_get
    ):
        mock_get.return_value.json.return_value = {

            "phylum":
                "pinophyta"
        }

        from api.views.views_info import (
            inferCanFlowerFromGBIF
        )

        self.assertFalse(

            inferCanFlowerFromGBIF(
                "pine"
            )

        )

    @patch(
        "api.views.views_info.requests.get"
    )
    def test_gbif_default_false(
            self,
            mock_get
    ):
        mock_get.return_value.json.return_value = {}

        from api.views.views_info import (
            inferCanFlowerFromGBIF
        )

        self.assertFalse(

            inferCanFlowerFromGBIF(
                "x"
            )

        )

    ################################
    # wikipedia
    ################################

    @patch(
        "api.views.views_info.requests.get"
    )
    def test_wiki_flowering(
            self,
            mock_get
    ):
        mock_get.return_value.status_code = 200

        mock_get.return_value.json.return_value = {

            "extract":
                "flowering plant"
        }

        from api.views.views_info import (
            getInfoFromWikipedia
        )

        result = (
            getInfoFromWikipedia(
                "rose"
            )
        )

        self.assertTrue(
            result[
                "canFlower"
            ]
        )

    @patch(
        "api.views.views_info.requests.get"
    )
    def test_wiki_gymnosperm(
            self,
            mock_get
    ):
        mock_get.return_value.status_code = 200

        mock_get.return_value.json.return_value = {

            "extract":
                "gymnosperm"
        }

        from api.views.views_info import (
            getInfoFromWikipedia
        )

        result = (
            getInfoFromWikipedia(
                "pine"
            )
        )

        self.assertFalse(
            result[
                "canFlower"
            ]
        )

    @patch(
        "api.views.views_info.inferCanFlowerFromGBIF"
    )
    @patch(
        "api.views.views_info.requests.get"
    )
    def test_wiki_fallback(
            self,
            mock_get,
            mock_gbif
    ):
        mock_gbif.return_value = True

        mock_get.return_value.status_code = 200

        mock_get.return_value.json.return_value = {

            "extract":
                "unknown text"
        }

        from api.views.views_info import (
            getInfoFromWikipedia
        )

        result = (
            getInfoFromWikipedia(
                "rose"
            )
        )

        self.assertTrue(
            result[
                "canFlower"
            ]
        )

    ################################
    # details=None branch
    ################################

    @patch(
        "api.views.views_info.saveOrUpdatePlant"
    )
    @patch(
        "api.views.views_info.getInfoFromWikipedia"
    )
    def test_filter_info_none(
            self,
            mock_wiki,
            mock_save
    ):
        mock_wiki.return_value = {

            "canFlower":
                True,

            "description":
                "desc"
        }

        from api.views.views_info import (
            filterInfo
        )

        result = (
            filterInfo(
                "Rose",
                None,
                "en"
            )
        )

        self.assertEqual(

            result[
                "minTemperature"
            ],

            2
        )

    ################################
    # translation branch
    ################################

    @patch(
        "api.views.views_info.saveOrUpdatePlant"
    )
    @patch(
        "api.views.views_info.translate_text"
    )
    def test_filter_translation(
            self,
            mock_translate,
            mock_save
    ):
        mock_translate.side_effect = [

            "rosa",

            "descripcion"
        ]

        from api.views.views_info import (
            filterInfo
        )

        result = (
            filterInfo(
                "Rose",
                {

                    "common_name":
                        "rose",

                    "family":
                        "Rosaceae",

                    "flowers":
                        True,

                    "description":
                        "desc",

                    "hardiness": {
                        "min": 1,
                        "max": 2
                    }

                },

                "es"
            )
        )

        self.assertEqual(
            result[
                "commonName"
            ],
            "rosa"
        )

    ################################
    # missing branches
    ################################

    @patch(
        "api.views.views_info.requests.get"
    )
    def test_gbif_exception(
        self,
        mock_get
    ):

        mock_get.side_effect=(
            Exception()
        )

        from api.views.views_info import (
            inferCanFlowerFromGBIF
        )

        self.assertFalse(

            inferCanFlowerFromGBIF(
                "rose"
            )

        )


    @patch(
        "api.views.views_info.requests.get"
    )
    def test_wiki_non_200(
        self,
        mock_get
    ):

        mock_get.return_value.status_code=404

        from api.views.views_info import (
            getInfoFromWikipedia
        )

        result=(
            getInfoFromWikipedia(
                "rose"
            )
        )

        self.assertIsNone(
            result[
                "canFlower"
            ]
        )


    @patch(
        "api.views.views_info.requests.get"
    )
    def test_wiki_exception(
        self,
        mock_get
    ):

        mock_get.side_effect=(
            Exception()
        )

        from api.views.views_info import (
            getInfoFromWikipedia
        )

        result=(
            getInfoFromWikipedia(
                "rose"
            )
        )

        self.assertFalse(
            result[
                "canFlower"
            ]
        )


    @patch(
        "api.views.views_info.requests.get"
    )
    def test_resolve_no_synonym(
        self,
        mock_get
    ):

        mock_get.return_value.raise_for_status=(
            lambda:None
        )

        mock_get.return_value.json.return_value={

            "species":
            "Lavandula"

        }

        result=(
            resolveScientificName(
                "lavender"
            )
        )

        self.assertEqual(
            result,
            "Lavandula"
        )


    @patch(
        "api.views.views_info.os.getenv"
    )
    def test_perenual_missing_key(
        self,
        mock_env
    ):

        mock_env.return_value=None

        from api.views.views_info import (
            getPlantInfoFromAPI
        )

        with self.assertRaises(
            RuntimeError
        ):

            getPlantInfoFromAPI(
                "rose"
            )


    @patch(
        "api.views.views_info.resolveScientificName"
    )
    @patch(
        "api.views.views_info.os.getenv"
    )
    @patch(
        "api.views.views_info.requests.get"
    )
    def test_perenual_426(
        self,
        mock_get,
        mock_env,
        mock_resolve
    ):

        mock_env.return_value=(
            "key"
        )

        mock_resolve.return_value=(
            "rose"
        )

        r1=type(
            "",
            (),
            {}
        )()

        r1.raise_for_status=(
            lambda:None
        )

        r1.json=lambda:{

            "data":[
                {
                    "id":123
                }
            ]
        }

        r2=type(
            "",
            (),
            {}
        )()

        r2.status_code=426

        mock_get.side_effect=[
            r1,
            r2
        ]

        from api.views.views_info import (
            getPlantInfoFromAPI
        )

        result=(
            getPlantInfoFromAPI(
                "rose"
            )
        )

        self.assertIsNone(
            result
        )


    def test_existing_plant_english(
        self
    ):

        Plant.objects.create(

            scientificName=
            "Rose",

            commonName=
            "Rose",

            family=
            "Rosaceae",

            canFlower=
            True,

            minTemperature=
            5,

            maxTemperature=
            30,

            description=
            "desc"
        )

        response=(
            self.client.get(
                self.URL,
                {
                    "scientificName":
                    "Rose",

                    "lang":
                    "en"
                }
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )

        data=(
            response.json()
        )

        self.assertEqual(
            data[
                "commonName"
            ],
            "Rose"
        )