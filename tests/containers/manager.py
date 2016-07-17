#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests for the attribute container manager."""

import unittest

from plaso.containers import manager

from tests.containers import test_lib


class AttributeContainersManagerTest(unittest.TestCase):
  """Tests for the attribute container manager."""

  def testAttributeContainerRegistration(self):
    """Tests the Register and DeregisterAttributeContainer functions."""
    # pylint: disable=protected-access
    number_of_classes = len(
        manager.AttributeContainersManager._attribute_container_classes)

    manager.AttributeContainersManager.RegisterAttributeContainer(
        test_lib.TestAttributeContainer)
    self.assertEqual(
        len(manager.AttributeContainersManager._attribute_container_classes),
        number_of_classes + 1)

    with self.assertRaises(KeyError):
      manager.AttributeContainersManager.RegisterAttributeContainer(
          test_lib.TestAttributeContainer)

    manager.AttributeContainersManager.DeregisterAttributeContainer(
        test_lib.TestAttributeContainer)
    self.assertEqual(
        len(manager.AttributeContainersManager._attribute_container_classes),
        number_of_classes)


if __name__ == '__main__':
  unittest.main()