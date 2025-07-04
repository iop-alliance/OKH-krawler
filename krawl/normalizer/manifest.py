# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2022 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
# SPDX-FileCopyrightText: 2022 Nicolas Traeder <nicolas@konek.to>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import validators

from krawl.dict_utils import DictUtils
from krawl.errors import ConversionError, NormalizerError, ParserError
from krawl.fetcher.result import FetchResult
from krawl.fetcher.util import convert_okh_v1_dict_to_losh
from krawl.log import get_child_logger
from krawl.model.agent import Agent, AgentRef, Organization, Person
from krawl.model.file import File, Image, ImageSlot, ImageTag
from krawl.model.hosting_id import HostingId
from krawl.model.hosting_unit import HostingUnitId
from krawl.model.hosting_unit_forge import HostingUnitIdForge
from krawl.model.language_string import LangStr
from krawl.model.licenses import LicenseCont
from krawl.model.licenses import get_by_expression_or_name_required as get_license
from krawl.model.outer_dimensions import OuterDimensions, OuterDimensionsOpenScad
from krawl.model.part import Part
from krawl.model.project import Project
from krawl.model.software import Software
from krawl.normalizer import Normalizer
from krawl.normalizer.file_handler import FileHandler
from krawl.recursive_type import RecDict
from krawl.util import extract_path as krawl_util_extract_path
from krawl.util import is_url

log = get_child_logger("manifest")

_user_re = re.compile(r'(?P<name>[^\[\(<]+)(\((?P<org>[^\)]*)\))?(<(?P<email>[^>]*)>)?')


class _ProjFilesInfo:

    def __init__(self,
                 hosting_unit_id: HostingUnitId,
                 manifest_contents_raw: RecDict,
                 file_handler: FileHandler | None = None):
        self._file_handler = file_handler
        self._fh_proj_info: dict | None = None
        self._hosting_unit_id: HostingUnitId = hosting_unit_id

        if self._file_handler:
            self._fh_proj_info = self._file_handler.gen_proj_info(self._hosting_unit_id, manifest_contents_raw)

    def files(self, raw_files: list[dict] | list[str] | dict | str | None) -> list[File]:
        files: list[File] = []
        if raw_files is None:
            pass
        elif isinstance(raw_files, list):
            for raw_file in raw_files:
                parsed_file = self.file(raw_file)
                if parsed_file:
                    files.append(parsed_file)
        elif isinstance(raw_files, (dict, str)):
            parsed_file = self.file(raw_files)
            if parsed_file:
                files.append(parsed_file)
        return files

    def _pre_parse_file(self, raw_file: str) -> dict:
        frozen_url: str | None
        if is_url(raw_file):
            # is URL
            url = raw_file
            if self._file_handler is None or (self._fh_proj_info is not None and
                                              not self._file_handler.is_home_hosting_url(self._fh_proj_info, url)):
                # NOTE We assume, that all platforms we do not support FileHandler for -
                #      i.e. we do not support frozen and non-frozen URLs for -
                #      use (only) non-frozen URLs.
                frozen_url = None
                path = self.extract_path(url)
            else:
                if self._fh_proj_info is None:
                    raise ValueError("Through the code logic of this software,"
                                     " it should be impossible to get here"
                                     " -> programmer error! (1)")
                path = Path(self._file_handler.extract_path(self._fh_proj_info, url))
                if self._file_handler.is_frozen_url(self._fh_proj_info, url):
                    frozen_url = url
                    url = self._file_handler.to_url(self._fh_proj_info, path, False)
                else:
                    frozen_url = self._file_handler.to_url(self._fh_proj_info, path, True)
        else:
            # is path relative to/within project/repo
            path = Path(raw_file)
            if path.is_absolute():
                raise ValueError(f"File path contained in manifest for project {self._hosting_unit_id} is absolute,"
                                 f" which is invalid!: '{raw_file}'")
            # path = str(path)
            if self._file_handler is None:
                url = self._hosting_unit_id.create_download_url(path)
                # NOTE Same as above assume, that all platforms we do not support FileHandler for -
                frozen_url = None
            else:
                if self._fh_proj_info is None:
                    raise ValueError("Through the code logic of this software,"
                                     " it should be impossible to get here"
                                     " -> programmer error! (2)")
                url = self._file_handler.to_url(self._fh_proj_info, path, False)
                frozen_url = self._file_handler.to_url(self._fh_proj_info, path, True)
        return {
            "path": path,
            "url": url,
            "frozen-url": frozen_url,
        }

    def extract_path(self, url: str) -> Path | None:
        """Extracts the repo-internal path from a forge URL.

        Args:
            url (str): Should represent a hosting platforms URL, pointing to a file in a repo.
        """
        try:
            hosting_unit_id, path = type(self._hosting_unit_id).from_url(url)
            if isinstance(hosting_unit_id, HostingUnitIdForge):
                path = hosting_unit_id.path
            return path
        except (ValueError, ParserError):
            return krawl_util_extract_path(url)

    def file(self, raw_file: dict | str | None) -> File | None:
        if raw_file is None:
            return None

        if isinstance(raw_file, str):
            try:
                file_dict = self._pre_parse_file(raw_file)
            except ValueError as err:
                log.error(f"Failed pre-parsing raw file: {err}")
                return None
        elif isinstance(raw_file, dict):
            file_dict = raw_file
        else:
            raise NormalizerError(f"Unsupported type for file: {type(raw_file)} - content:\n{raw_file}")

        file = File()
        # NOTE Better not set this, as this path is not relative to the project root
        # file.path = DictUtils.to_path(file_dict.get("path"))
        # NOTE Better not set the file name
        #      as the files human readable name,
        #      as that can also always be done later, if deemed necessary.
        #file.name = str(file.path.with_suffix("").name) if file.path and file.path.name else None
        file.mime_type = DictUtils.to_string(file_dict.get("mime-type"))
        # In case it was not provided,
        # this tries to evaluate it from the file extension
        file.mime_type = file.evaluate_mime_type()

        url = DictUtils.to_string(file_dict.get("url"))
        if url and validators.url(url):
            file.url = url
        frozen_url = DictUtils.to_string(file_dict.get("frozen-url"))
        if frozen_url and validators.url(frozen_url):
            file.frozen_url = frozen_url

        file.created_at = DictUtils.to_datetime(file_dict.get("created-at"))
        file.last_changed = DictUtils.to_datetime(file_dict.get("last-changed"))
        # file.last_visited = datetime.now(timezone.utc)
        # file.license = get_license(DictUtils.to_string(file_dict.get("license")))
        # file.licensor = DictUtils.to_string(file_dict.get("licensor"))

        return file


class ManifestNormalizer(Normalizer):

    def __init__(self, file_handler: FileHandler | None = None):
        self._file_handler = file_handler
        self.files_info: _ProjFilesInfo = None

    def extract_required_str(self, raw: dict, key: str) -> str:
        value: str | None = DictUtils.to_string(raw.get(key))
        if not value:
            raise NormalizerError(f"Manifest is missing required key: {key}")
        return value

    def normalize(self, fetch_result: FetchResult) -> Project:
        try:
            raw: RecDict = fetch_result.data.as_dict()
        except ValueError as err:
            raise NormalizerError(f"Failed to parse manifest: {err}") from err

        okhv_fetched = raw.get("okhv", None)
        if okhv_fetched is None:
            # We assume it is OKH v1
            try:
                raw = convert_okh_v1_dict_to_losh(raw)
            except ConversionError as err:
                raise NormalizerError(f"Failed to convert OKH v1 manifest to new version: {err}") from err

        hosting_unit_id = fetch_result.data_set.hosting_unit_id

        log.debug("normalizing manifest of '%s'", hosting_unit_id)

        self.files_info = _ProjFilesInfo(hosting_unit_id, raw, self._file_handler)

        license = self._license_from_container_dict(raw)
        if not license:
            raise ValueError("'license' is None, which should not be possible at this point")
        licensor = self._licensor_from_container_dict(hosting_unit_id, raw)
        if not licensor:
            raise ValueError("'licensor' is None, which should not be possible at this point")
        project = Project(
            name=self.extract_required_str(raw, "name"),
            repo=self.extract_required_str(raw, "repo"),
            license=license,
            licensor=licensor,
        )
        project.version = DictUtils.to_string(raw.get("version"))
        project.release = DictUtils.to_string(raw.get("release"))
        project.organization = self._organizations(raw.get("organization"))
        project.readme = self.files_info.files(raw.get("readme"))
        project.contribution_guide = self.files_info.file(raw.get("contribution-guide"))
        project.image = self._images(raw.get("image"))
        project.function = DictUtils.to_string(raw.get("function"))
        project.documentation_language = self._clean_language(raw.get("documentation-language"))
        project.technology_readiness_level = DictUtils.to_string(raw.get("technology-readiness-level"))
        project.documentation_readiness_level = DictUtils.to_string(raw.get("documentation-readiness-level"))
        project.attestation = DictUtils.to_string_list(raw.get("attestation"))
        project.publication = DictUtils.to_string_list(raw.get("publication"))
        project.standard_compliance = DictUtils.to_string_list(raw.get("standard-compliance"))
        project.cpc_patent_class = DictUtils.to_string(raw.get("cpc-patent-class"))
        project.tsdc = DictUtils.to_string(raw.get("tsdc"))
        project.bom = self.files_info.files(raw.get("bom"))
        project.manufacturing_instructions = self.files_info.files(raw.get("manufacturing-instructions"))
        project.user_manual = self.files_info.files(raw.get("user-manual"))
        try:
            project.outer_dimensions = self._outer_dimensions(raw.get("outer-dimensions"))
        except (ParserError, NormalizerError) as err:
            log.warn("Failed parsing outer-dimensions: %s", err)
        project.part = self._parts(raw.get("part"))
        project.software = self._software(hosting_unit_id, raw.get("software"))

        return project

    @classmethod
    def _host(cls, raw: dict) -> str | None:  # NOTE Unused, can probably be removed
        manifest = raw["manifest"]
        host = DictUtils.to_string(manifest.get("dataHost"))
        if host:
            return host
        repo = DictUtils.to_string(raw.get("repo"))
        if not repo:
            return None
        repo_url = urlparse(repo)
        host = repo_url.netloc.split(":")[0]
        if host:
            return host
        return None

    def _image_slots(self, raw: Any) -> set[ImageSlot]:
        slots: set[ImageSlot] = set()
        if raw is None:
            return slots
        if isinstance(raw, list):
            for raw_item in raw:
                if isinstance(raw_item, str):
                    tag = ImageSlot(raw_item)
                    slots.add(tag)
        return slots

    def _image_tags(self, raw: Any) -> set[ImageTag]:
        tags: set[ImageTag] = set()
        if raw is None:
            return tags
        if isinstance(raw, list):
            for raw_item in raw:
                if isinstance(raw_item, str):
                    tag = ImageTag(raw_item)
                    tags.add(tag)
        return tags

    def _image_depicts_strings(self, raw: Any, default_language: str = 'en') -> set[LangStr]:
        depicts: set[LangStr] = set()
        if raw is None:
            return depicts
        if isinstance(raw, (str, dict, LangStr)):
            raw = [raw]
        if isinstance(raw, list):
            for raw_item in raw:
                if isinstance(raw_item, str):
                    cont = LangStr(raw_item, default_language)
                elif isinstance(raw_item, dict):
                    text = raw_item.get("text")
                    if not text:
                        raise ValueError(f"Missing property 'text' for language string for image depicts:\n{raw_item}")
                    language = raw_item.get("language", default_language)
                    cont = LangStr(text, language)
                elif isinstance(raw_item, LangStr):
                    cont = raw_item
                else:
                    raise TypeError(f"Unsupported type for image depicts: {type(raw_item)} - content:\n{raw_item}")
                depicts.add(cont)
        return depicts

    def _license_from_container_dict(self, raw: dict, required: bool = True) -> LicenseCont | None:
        # license_raw = self.extract_required_str(raw, "license")
        license_raw = raw.get("license")
        if not license_raw:
            license_raw = raw.get("spdx-license")  # NOTE Deprecated property
            if license_raw:
                log.warn("Missing required key 'license' in manifest, but found deprecated key 'spdx-license'")
        if not license_raw:
            license_raw = raw.get("alternative-license")  # NOTE Deprecated property
            if license_raw:
                log.warn("Missing required key 'license' in manifest, but found deprecated key 'alternative-license'")
        if not license_raw:
            if required:
                raise NormalizerError("Missing required key 'license' in manifest")
            return None
        if not isinstance(license_raw, str):
            raise NormalizerError(
                f"Failed to normalize license: should be of type str, but is of type: {type(license_raw)} - content:\n{license_raw}"
            )
        log.debug("license_raw: %s", license_raw)
        try:
            license_cont: list[LicenseCont] | None = get_license(license_raw)
            if not license_cont:
                if required:
                    raise NormalizerError(
                        f"Invalid SPDX license expression '{license_raw}' - did not map to any license")
                return None
            if license_cont and len(license_cont) > 1:
                additional_licenses = ', '.join([license.id() for license in license_cont[1:]])
                log.warn(f"Silently ignore additional licenses: {additional_licenses}")
            return license_cont[0]
        except ValueError as err:
            raise NormalizerError(f"Failed to normalize license: {err}") from err
        except NameError as err:
            raise NormalizerError(f"Failed to normalize license: {err}") from err

    def _licensor_from_container_dict(self,
                                      hosting_unit_id: HostingUnitId,
                                      raw: dict,
                                      required: bool = True) -> list[Agent | AgentRef] | None:
        licensor_raw = raw.get("licensor")
        # HACK Necessary until Appropedia switches to the new OKH format
        #      (they are still on v1 as of January 2025),
        #      which allows for multiple licensors.
        if hosting_unit_id.hosting_id() == HostingId.APPROPEDIA_ORG:
            if isinstance(licensor_raw, str):
                users = [user.strip() for user in licensor_raw.split(',')]
                user_ids = [{
                    "name": user.replace('User:', ''),
                    "url": f"https://www.appropedia.org/{user}",
                } for user in users]
                licensor_raw = user_ids
        licensor = self._agents(licensor_raw)
        if not licensor:
            if required:
                raise NormalizerError("Missing required key 'licensor' in manifest (or parsing of it failed)")
                return None
        return licensor

    def _person_from_user_str(self, user: str) -> Person:
        # `user` is e.g:
        # - 'Firstname Lastname'
        # - 'Firstname Lastname <foo@bar.edu>'
        # - 'Firstname Lastname (Some Organization) <foo@bar.edu>'
        match_res = _user_re.match(user.strip())
        if match_res:
            name = match_res.group('name')
            name = name.strip() if name else name
            email = match_res.group('email')
            email = email.strip() if email else email
            return Person(
                name=name,
                email=email,
            )
        return Person(name=user)

    def _agent(self, raw: Any) -> Agent | AgentRef | None:
        agent: Person | AgentRef | None = None
        if not raw:
            return agent
        if isinstance(raw, str):
            agent = self._person_from_user_str(raw)
        elif isinstance(raw, dict):
            if "iri" in raw:
                agent = AgentRef(
                    iri=self.extract_required_str(raw, "iri"),
                    type=self.extract_required_str(raw, "type"),
                )
            else:
                agent = Person(
                    name=self.extract_required_str(raw, "name"),
                    email=raw.get("email"),
                    # organization=raw.get("organization"),
                    url=raw.get("url"),
                )
        return agent

    def _agents(self, raw: Any) -> list[Agent | AgentRef]:
        agents: list[Agent | AgentRef] = []
        if raw is None:
            return agents
        if isinstance(raw, list):
            for raw_item in raw:
                agent = self._agent(raw_item)
                if agent:
                    agents.append(agent)
        else:
            agent = self._agent(raw)
            if agent:
                agents.append(agent)
        return agents

    def _organization(self, raw: Any) -> Organization | AgentRef | None:
        agent: Organization | AgentRef | None = None
        if not raw:
            return agent
        if isinstance(raw, str):
            agent = Organization(name=raw)
        elif isinstance(raw, dict):
            if "iri" in raw:
                agent = AgentRef(
                    iri=self.extract_required_str(raw, "iri"),
                    type=self.extract_required_str(raw, "type"),
                )
            else:
                agent = Organization(
                    name=self.extract_required_str(raw, "name"),
                    email=raw.get("email"),
                    # organization=raw.get("organization"),
                    url=raw.get("url"),
                )
        return agent

    def _organizations(self, raw: Any) -> list[Organization | AgentRef]:
        organizations: list[Organization | AgentRef] = []
        if raw is None:
            return organizations
        if isinstance(raw, list):
            for raw_item in raw:
                organization = self._organization(raw_item)
                if organization:
                    organizations.append(organization)
        else:
            organization = self._organization(raw)
            if organization:
                organizations.append(organization)
        return organizations

    def _images(self, raw: Any) -> list[Image]:
        images: list[Image] = []
        if raw is None:
            return images
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, list):
            for raw_item in raw:
                image_file = self.files_info.file(raw_item)
                if not image_file:
                    continue
                image = Image.from_file(image_file)
                if isinstance(raw_item, dict):
                    image.slots = self._image_slots(raw_item.get("slots"))
                    image.tags = self._image_tags(raw_item.get("tags"))
                    image.depicts = self._image_depicts_strings(raw_item.get("depicts"))
                images.append(image)
        else:
            raise TypeError(f"Unsupported type for images: {type(raw)}")
        return images

    def _parts(self, raw_parts: Any) -> list[Part]:
        if raw_parts is None or not isinstance(raw_parts, list):
            return []
        parts = []
        for raw_part in raw_parts:
            name = DictUtils.to_string(raw_part.get("name"))
            if not name:
                raise NormalizerError("Part is missing required property 'name'")
            part = Part(
                name=name,
                name_clean=DictUtils.clean_name(name),
            )
            part.image = self._images(raw_part.get("image"))
            part.source = self.files_info.files(raw_part.get("source"))
            part.export = self.files_info.files(raw_part.get("export"))
            part.material = DictUtils.to_string(raw_part.get("material"))
            part.manufacturing_instructions = self.files_info.files(raw_part.get("manufacturing-instructions"))
            part.mass = DictUtils.to_float(raw_part.get("mass"))
            try:
                part.outer_dimensions = self._outer_dimensions(raw_part.get("outer-dimensions"))
            except (ParserError, NormalizerError) as err:
                log.warn("Failed parsing outer-dimensions: %s", err)
            part.tsdc = DictUtils.to_string(raw_part.get("tsdc"))
            parts.append(part)
        DictUtils.ensure_unique_clean_names(parts)
        return parts

    def _software_from_dict(self, hosting_unit_id: HostingUnitId, raw_software: dict) -> Software:
        release = DictUtils.to_string(raw_software.get("release"))
        if not release:
            raise NormalizerError(
                f"Software entry in manifest {hosting_unit_id} is missing required property 'release'")
        sw = Software(release=release)
        sw.installation_guide = self.files_info.file(raw_software.get("installation-guide"))
        sw.documentation_language = self._clean_language(raw_software.get("documentation-language"))
        sw.license = self._license_from_container_dict(raw_software, False)
        sw.licensor = self._licensor_from_container_dict(hosting_unit_id, raw_software, False)
        sw.organization = self._organizations(raw_software.get("organization"))
        return sw

    def _software(self, hosting_unit_id: HostingUnitId, raw_software: Any) -> list[Software]:
        software: list[Software] = []
        if raw_software is None:
            return software
        if isinstance(raw_software, list):
            for rs in raw_software:
                sws = self._software(hosting_unit_id, rs)
                software.extend(sws)
        elif isinstance(raw_software, dict):
            sw = self._software_from_dict(hosting_unit_id, raw_software)
            software.append(sw)
        else:
            raise TypeError(f"Unsupported type for software: {type(raw_software)} - content:\n{raw_software}")
        return software

    @classmethod
    def _outer_dimensions(cls, raw_outer_dimensions: Any) -> OuterDimensions | None:
        if not raw_outer_dimensions:
            return None
        if not isinstance(raw_outer_dimensions, dict):
            raise ParserError("Can only parse dict as outer dimensions")
        try:
            return OuterDimensions.from_dict(raw_outer_dimensions)
        except ParserError as err:
            try:
                return OuterDimensions.from_openscad(OuterDimensionsOpenScad.from_dict(raw_outer_dimensions))
            except ParserError as err2:
                raise ParserError("Failed to parse outer dimensions, both as new and as old format:"
                                  f"\n- '{err}'\n- '{err2}'") from err


# __test_od_data = {'unit': 'm', 'openSCAD': '13'}
# OuterDimensions.from_openscad(OuterDimensionsOpenScad.from_dict(__test_od_data))
