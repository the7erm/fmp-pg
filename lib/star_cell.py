#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
# Copyright 2013 Eugene R. Miller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# This code comes from lots of different sources:
# http://faq.pygtk.org/index.py?req=show&file=faq13.045.htp # Create a custom gtk.CellRenderer
# http://faq.pygtk.org/index.py?req=show&file=faq13.041.htp # How to add images/animations
# http://nullege.com/codes/show/src%40t%40r%40translate-HEAD%40src%40trunk%40virtaal%40virtaal%40views%40widgets%40cellrendererwidget.py/147/gtk.CellEditable/python # how to add a widget.

import gtk, random
import pango, os, sys
import gtk, pygtk, gobject
from gobject import idle_add, PARAM_READWRITE, SIGNAL_RUN_FIRST, TYPE_PYOBJECT
from __init__ import gtk_main_quit

img_path = ""
# print sys.path[0]
if os.path.isfile(sys.path[0]+"/images/star.grey.png"):
    img_path = sys.path[0]+"/"
elif os.path.isfile(sys.path[0]+"/../images/star.grey.png"):
    img_path = sys.path[0]+"/../"
elif os.path.isfile("../images/star.grey.png"):
    img_path = "../"
elif os.path.isfile(sys.path[0]+"../images/star.grey.png"):
    img_path = sys.path[0]+"../"


star_grey = gtk.gdk.pixbuf_new_from_file(img_path+"images/star.grey.png")
star_hover = gtk.gdk.pixbuf_new_from_file(img_path+"images/star.selected.png")
star_selected = gtk.gdk.pixbuf_new_from_file(img_path+"images/star.hover.png")
no_star = gtk.gdk.pixbuf_new_from_file(img_path+"images/no.star.png")
no_star_selected = gtk.gdk.pixbuf_new_from_file(img_path+"images/no.star.selected.png")
no_star_grey = gtk.gdk.pixbuf_new_from_file(img_path+"images/no.star.grey.png")


class CellRendererStar(gtk.GenericCellRenderer):

	__gproperties__ = {
		"rating": (gobject.TYPE_INT, "Rating", "Rating", 0, 10, 0, gobject.PARAM_READWRITE),
	}

	def __init__(self, size=30, data_col=1):
		self.__gobject_init__()
		self.props.mode = gtk.CELL_RENDERER_MODE_EDITABLE
		self.image = None
		self.rating = None
		self.size = size
		self.star_grey = star_grey.scale_simple(self.size, self.size, gtk.gdk.INTERP_BILINEAR)
		self.star_selected = star_selected.scale_simple(self.size, self.size, gtk.gdk.INTERP_BILINEAR)
		self.star_hover = star_hover.scale_simple(self.size, self.size, gtk.gdk.INTERP_BILINEAR)
		self.no_star = no_star.scale_simple(self.size, self.size, gtk.gdk.INTERP_BILINEAR)
		self.no_star_grey = no_star_grey.scale_simple(self.size, self.size, gtk.gdk.INTERP_BILINEAR)
		self.no_star_selected = no_star_selected.scale_simple(self.size, self.size, gtk.gdk.INTERP_BILINEAR)
		self.rating = -1
		self.editablemap = {}
		self.stars_hover = {}
		self.stars = {}
		self.data_col = data_col
		self._starting_edit = False


	def do_set_property(self, pspec, value):
		# print "PSPEC:",pspec.name,"=",value
		if pspec.name == 'rating':
			if value != self.rating:
				# print "REMADE!"
				self.rating = value
				self.make_stars()
		setattr(self, pspec.name, value)
	
	def make_stars(self):
		if self.rating == -1:
			return
		rating = self.rating
		if self.stars.has_key(rating):
			self.image = self.stars[rating]
			self.image.show()
			return

		self.image = gtk.Image()
		self.image.show()
		
		# self.widget.value = rating
		num_of_stars = 6
		target_width = self.size * num_of_stars
		target_height = self.size
		# gtk.gdk.Pixbuf(colorspace, has_alpha, bits_per_sample, width, height)
		self.pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, target_width, target_height)
		for i in range(0,num_of_stars,1):
			if i == 0:
				if rating == 0:
					self.no_star.copy_area(
						0, # src_x
						0, # src_y
						self.size, # width
						self.size, # height
						self.pb, # dest_pixbuf
						(i*self.size), # dest_x
						0, # dest_y
					)
				elif rating >= i:
					self.no_star_selected.copy_area(
						0, # src_x
						0, # src_y
						self.size, # width
						self.size, # height
						self.pb, # dest_pixbuf
						(i*self.size), # dest_x
						0, # dest_y
					)
				else:
					self.no_star_grey.copy_area(
						0, # src_x
						0, # src_y
						self.size, # width
						self.size, # height
						self.pb, # dest_pixbuf
						(i*self.size), # dest_x
						0, # dest_y
					)
				continue
			if rating >= i:
				# copy_area(src_x, src_y, width, height, dest_pixbuf, dest_x, dest_y)
				self.star_selected.copy_area(
					0, # src_x
					0, # src_y
					self.size, # width
					self.size, # height
					self.pb, # dest_pixbuf
					(i*self.size), # dest_x
					0, # dest_y
				)
			else:
				self.star_grey.copy_area(
					0, # src_x
					0, # src_y
					self.size, # width
					self.size, # height
					self.pb, # dest_pixbuf
					(i*self.size), # dest_x
					0, # dest_y
				)
	
		
		self.image.set_from_pixbuf(self.pb)
		self.image.show()
		self.stars[rating] = self.image

	def make_stars_hover(self, rating):
		if self.rating == -1:
			return
		self.image = gtk.Image()
		self.image.show()
		if self.stars_hover.has_key(rating):
			self.image = self.stars_hover[rating]
			self.image.show()
			return
		
		num_of_stars = 6
		target_width = self.size * num_of_stars
		target_height = self.size
		self.pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, target_width, target_height)
		for i in range(0,num_of_stars,1):
			if i == 0:
				if rating == 0:
					self.no_star.copy_area(
						0, # src_x
						0, # src_y
						self.size, # width
						self.size, # height
						self.pb, # dest_pixbuf
						(i*self.size), # dest_x
						0, # dest_y
					)
				elif rating >= i:
					self.no_star_selected.copy_area(
						0, # src_x
						0, # src_y
						self.size, # width
						self.size, # height
						self.pb, # dest_pixbuf
						(i*self.size), # dest_x
						0, # dest_y
					)
				else:
					self.no_star_grey.copy_area(
						0, # src_x
						0, # src_y
						self.size, # width
						self.size, # height
						self.pb, # dest_pixbuf
						(i*self.size), # dest_x
						0, # dest_y
					)
				continue
			if rating >= i:
				# copy_area(src_x, src_y, width, height, dest_pixbuf, dest_x, dest_y)
				self.star_hover.copy_area(
					0, # src_x
					0, # src_y
					self.size, # width
					self.size, # height
					self.pb, # dest_pixbuf
					(i*self.size), # dest_x
					0, # dest_y
				)
			else:
				self.star_grey.copy_area(
					0, # src_x
					0, # src_y
					self.size, # width
					self.size, # height
					self.pb, # dest_pixbuf
					(i*self.size), # dest_x
					0, # dest_y
				)
	

		self.image.set_from_pixbuf(self.pb)
		self.image.show()
		self.stars_hover[rating] = self.image

	def do_get_property(self, pspec):
		return getattr(self, pspec.name)

	def func(self, model, path, iter, (image, tree)):
		# print "FUNC:",model,path,iter, (image, tree)
		if model.get_value(iter, 0) == image:
			self.redraw = 1
			cell_area = tree.get_cell_area(path, tree.get_column(0))
			tree.queue_draw_area(cell_area.x, cell_area.y, cell_area.width, cell_area.height)

	def animation_timeout(self, tree, image):
		if image.get_storage_type() == gtk.IMAGE_ANIMATION:
			self.redraw = 0
			image.get_data('iter').advance()
			model = tree.get_model()
			model.foreach(self.func, (image, tree))
			if self.redraw:
				gobject.timeout_add(image.get_data('iter').get_delay_time(),
					self.animation_timeout, tree, image)
			else:
				image.set_data('iter', None)

	def on_activate(event, widget, path, background_area, cell_area, flags):
		print "ON_ACTIVATE:",event, widget, path, background_area, cell_area, flags


	def on_button_press(self, tree, event):
		#  "on_button_press:", tree, event
		try:
			path, col, x, y = tree.get_path_at_pos(int(event.x), int(event.y))
		except TypeError:
			return
		rends = col.get_cell_renderers()
		try:
			if rends[0] != self:
				return
		except IndexError:
			print "INDEX ERROR"
			return
		cell_area = tree.get_cell_area(path, tree.get_column(0))
		rating = x / self.size
		# print "x, y:", x, y
		model = tree.get_model()
		model[path][self.data_col] = rating
		expose_area = tree.get_background_area(path, col)
		flags = gtk.CELL_RENDERER_SELECTED
		self.make_stars_hover(rating)
		self.on_render(tree.get_bin_window(), tree, 
					   tree.get_background_area(path, col), 
					   tree.get_cell_area(path, col), expose_area, flags)

	def on_motion_notify(self, tree, event):
		try:
			path, col, x, y = tree.get_path_at_pos(int(event.x), int(event.y))
		except TypeError:
			return
		
		rends = col.get_cell_renderers()
		
		flags = 0
		
		try:
			if rends[0] != self:
				return
		except IndexError:
			return
		expose_area = background_area = tree.get_background_area(path, col)
		cell_area = tree.get_cell_area(path, tree.get_column(0))
		x = event.x
		y = event.y
		window = tree.get_bin_window()
		x, y, mask = window.get_pointer()

		if x > (expose_area.x+5) and int(x) < (expose_area.x + (expose_area.width-5)) and int(y) > expose_area.y and int(y) < (expose_area.y + cell_area.height):
			# print "IN!"
			flags = gtk.CELL_RENDERER_PRELIT
		
		# self.make_stars_hover(rating)
		self.on_render(window, tree, background_area , tree.get_cell_area(path, col), expose_area, flags)
		
		

	def on_render(self, window, widget, background_area, cell_area, expose_area, flags):
		self.props.mode = gtk.CELL_RENDERER_MODE_INERT
		if not self.image:
			return
		
		# self.make_stars()
		if flags & gtk.CELL_RENDERER_PRELIT:
			x, y, mask = window.get_pointer()
			try:
				# print "background_area:",background_area
				path, col, _x, _y = widget.get_path_at_pos(int(x), int(y))
				
				if x > background_area.x and x < (background_area.x + background_area.width) and y > background_area.y and y < (background_area.y + background_area.height):
					# print "x:(%s) > xa:(%s) and x:(%s) < xa+w:(%s)" % (_x, background_area.x, _x, (background_area.x + background_area.width) )
					rating = _x / self.size
					self.make_stars_hover(rating)
				else:
					# print "OUT!"
					self.make_stars()
				
				# self.make_stars_hover(rating)
			except TypeError:
				# print "TYPEERROR!"
				self.make_stars()
		else:
			self.make_stars()
		
		pix_rect = gtk.gdk.Rectangle()
		pix_rect.x, pix_rect.y, pix_rect.width, pix_rect.height = self.on_get_size(widget, cell_area)

		pix_rect.x += cell_area.x
		pix_rect.y += cell_area.y
		pix_rect.width  -= 2 * self.get_property("xpad")
		pix_rect.height -= 2 * self.get_property("ypad")

		draw_rect = cell_area.intersect(pix_rect)
		draw_rect = expose_area.intersect(draw_rect)

		pix = self.image.get_pixbuf()
		
		
		window.draw_pixbuf(widget.style.black_gc, pix, draw_rect.x-pix_rect.x, draw_rect.y-pix_rect.y, draw_rect.x, draw_rect.y, draw_rect.width, draw_rect.height, gtk.gdk.RGB_DITHER_NONE, 0, 0)

	def on_get_size(self, widget, cell_area):
		if not self.image:
			return 0, 0, 0, 0

		if self.image.get_storage_type() == gtk.IMAGE_ANIMATION:
			animation = self.image.get_animation()
			pix_rect = animation.get_iter().get_pixbuf()
		elif self.image.get_storage_type() == gtk.IMAGE_PIXBUF:
			pix = self.image.get_pixbuf()
		else:
			return 0, 0, 0, 0
		pixbuf_width  = pix.get_width()
		pixbuf_height = pix.get_height()
		calc_width  = self.get_property("xpad") * 2 + pixbuf_width
		calc_height = self.get_property("ypad") * 2 + pixbuf_height
		x_offset = 0
		y_offset = 0
		if cell_area and pixbuf_width > 0 and pixbuf_height > 0:
			x_offset = self.get_property("xalign") * (cell_area.width - calc_width -  self.get_property("xpad"))
			y_offset = self.get_property("yalign") * (cell_area.height - calc_height -  self.get_property("ypad"))
		# print "on_get_size:",x_offset, y_offset, calc_width, calc_height
		return x_offset, y_offset, calc_width, calc_height


gobject.type_register(CellRendererStar)

if __name__ == "__main__":
	class Tree(gtk.TreeView):
		def __init__(self):
			self.store = gtk.ListStore(str, int, int)
			gtk.TreeView.__init__(self)
			self.set_model(self.store)
			self.set_headers_visible(True)

			self.append_column(gtk.TreeViewColumn('First', gtk.CellRendererText(), text=0))
			# self.append_column(gtk.TreeViewColumn('Second', CellRendererWidget(lambda widget:widget.get_label()), widget=1))
			cell = CellRendererStar(30,1)
			cell.set_property('xalign',0.0)
			self.append_column(gtk.TreeViewColumn('Erm', cell, rating=1))
			self.connect("motion-notify-event", cell.on_motion_notify)
			self.connect("button-press-event", cell.on_button_press)

			cell = CellRendererStar(30,2)
			cell.set_property('xalign',0.0)
			self.append_column(gtk.TreeViewColumn('Steph', cell, rating=2))
			
			self.connect("motion-notify-event", cell.on_motion_notify)
			self.connect("button-press-event", cell.on_button_press)

			self.connect("key-release-event", self.on_key_release)

			self.set_property('reorderable',True)
			self.set_property('rubber-banding', True)
			select = self.get_selection()
			select.set_mode(gtk.SELECTION_MULTIPLE)

		def insert(self, name):
			for r in range(1,20):
				self.store.append(["%s.%s" % (r, name), random.randint(0, 7), random.randint(0, 7)])

		def on_key_release(self, widget, event):
			print "on_key_release:",event.keyval,'string:', event.string, 'keycode:', event.hardware_keycode, 'state:',event.state

			if event.hardware_keycode == 119 and event.state == 0:
				selection = self.get_selection()
				selected_rows = selection.get_selected_rows()
				print "selected_rows:",selected_rows
				liststore, rows = selected_rows
				rows.reverse()
				for r in rows:
					del liststore[r]

	def on_change(*args):
		print "CHANGED!", args

	w = gtk.Window()
	w.set_position(gtk.WIN_POS_CENTER)
	w.connect('delete-event', gtk_main_quit)
	t = Tree()
	m = t.get_model()
	m.connect("row-changed", on_change)
	t.insert('foo')
	w.add(t)

	w.show_all()
	gtk.main()
